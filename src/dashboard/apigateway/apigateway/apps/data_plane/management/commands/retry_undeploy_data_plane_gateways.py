#
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - API 网关 (BlueKing - APIGateway) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.
#
import logging
import time
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apigateway.apps.data_plane.management.commands.gateway_data_plane_command_utils import (
    AuditWriter,
    parse_gateway_names,
)
from apigateway.apps.data_plane.models import DataPlane, GatewayDataPlaneBinding
from apigateway.controller.constants import DELETE_PUBLISH_ID
from apigateway.controller.tasks.syncing import revoke_release
from apigateway.core.models import Gateway, Release

logger = logging.getLogger(__name__)

DEFAULT_REVOKE_INTERVAL_SECONDS = 60


class Command(BaseCommand):
    help = (
        "Retry undeploying already-unbound gateways from one data plane by re-triggering synchronous revoke. "
        "This command does not change gateway data-plane bindings or stage status."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--gateway-names", type=str, default="", help="Gateway names, comma separated")
        parser.add_argument(
            "--gateway-names-file",
            type=str,
            default="",
            help="Gateway names file, one gateway name per line",
        )
        parser.add_argument("--data-plane-name", type=str, required=True, help="Target data plane name")
        parser.add_argument("--log-file", type=str, required=True, help="Audit log file path")
        parser.add_argument("--operator", type=str, default="system", help="Operator username")
        parser.add_argument("--dry-run", action="store_true", help="Preview retries without executing")
        parser.add_argument(
            "--interval-seconds",
            type=int,
            default=DEFAULT_REVOKE_INTERVAL_SECONDS,
            help="Seconds to wait after triggering each release revoke (default: 60)",
        )

    def _retry_gateway(
        self,
        gateway: Gateway,
        releases: list[Release],
        data_plane: DataPlane,
        operator: str,
        dry_run: bool,
        interval_seconds: int,
        audit_writer: AuditWriter,
    ) -> bool:
        audit_log_common_args = {
            "action": "retry_undeploy_data_plane_gateway",
            "operator": operator,
            "gateway_id": gateway.id,
            "gateway_name": gateway.name,
            "data_plane_id": data_plane.id,
            "data_plane_name": data_plane.name,
        }

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] would retry undeploy gateway={gateway.name} from data_plane={data_plane.name}"
            )
            audit_writer.write(result="success", reason="dry_run", **audit_log_common_args)
            return True

        all_triggered = True
        for release in releases:
            try:
                ok = revoke_release(
                    release_id=release.id,
                    publish_id=DELETE_PUBLISH_ID,
                    data_plane_id=data_plane.id,
                )
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "failed to retry undeploy release: gateway=%s, release=%s, data_plane=%s",
                    gateway.name,
                    release.id,
                    data_plane.name,
                )
                all_triggered = False
                continue

            if not ok:
                all_triggered = False
            if interval_seconds:
                time.sleep(interval_seconds)

        if all_triggered:
            audit_writer.write(result="success", **audit_log_common_args)
        else:
            audit_writer.write(result="failed", reason="revoke_failed", **audit_log_common_args)
        return all_triggered

    def handle(self, *args, **options) -> None:
        gateway_names = parse_gateway_names(options["gateway_names"], options["gateway_names_file"])
        data_plane_name = options["data_plane_name"].strip()
        operator = options["operator"]
        dry_run = options["dry_run"]
        interval_seconds = options.get("interval_seconds", DEFAULT_REVOKE_INTERVAL_SECONDS)
        audit_writer = AuditWriter(self.stdout, options["log_file"])

        if not data_plane_name:
            raise CommandError("data_plane_name should not be empty")
        if interval_seconds < 0:
            raise CommandError("interval_seconds should not be negative")

        data_plane = DataPlane.objects.filter(name=data_plane_name).first()
        if not data_plane:
            raise CommandError(f"data plane not found: {data_plane_name}")

        gateways = list(Gateway.objects.filter(name__in=gateway_names))
        gateway_by_name = {gateway.name: gateway for gateway in gateways}
        not_found_gateway_names = set(gateway_names) - set(gateway_by_name)
        if not_found_gateway_names:
            raise CommandError(f"some gateway names not found in the database: {not_found_gateway_names}")

        rebound_gateway_names = set(
            GatewayDataPlaneBinding.objects.filter(
                gateway_id__in=[gateway.id for gateway in gateways],
                data_plane_id=data_plane.id,
            ).values_list("gateway__name", flat=True)
        )
        if rebound_gateway_names:
            raise CommandError(
                f"some gateways are still bound to data plane={data_plane_name}: {rebound_gateway_names}"
            )

        releases_by_gateway_id = defaultdict(list)
        for release in Release.objects.filter(gateway_id__in=[gateway.id for gateway in gateways]).order_by("id"):
            releases_by_gateway_id[release.gateway_id].append(release)

        success_count = 0
        failed_count = 0
        skipped_count = 0
        for gateway_name in gateway_names:
            gateway = gateway_by_name[gateway_name]
            releases = releases_by_gateway_id[gateway.id]
            if not releases:
                audit_writer.write(
                    action="retry_undeploy_data_plane_gateway",
                    result="skipped",
                    reason="no_releases",
                    operator=operator,
                    gateway_id=gateway.id,
                    gateway_name=gateway.name,
                    data_plane_id=data_plane.id,
                    data_plane_name=data_plane.name,
                )
                skipped_count += 1
                continue

            if self._retry_gateway(
                gateway=gateway,
                releases=releases,
                data_plane=data_plane,
                operator=operator,
                dry_run=dry_run,
                interval_seconds=interval_seconds,
                audit_writer=audit_writer,
            ):
                success_count += 1
            else:
                failed_count += 1

        summary = f"retry undeploy finished: success={success_count}, failed={failed_count}, skipped={skipped_count}"
        if failed_count:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
