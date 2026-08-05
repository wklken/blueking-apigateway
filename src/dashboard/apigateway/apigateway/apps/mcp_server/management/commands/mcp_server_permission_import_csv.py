# -*- coding: utf-8 -*-
#
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - API 网关(BlueKing - APIGateway) available.
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
import csv
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apigateway.apps.mcp_server.constants import MCPServerAppPermissionGrantTypeEnum
from apigateway.apps.mcp_server.models import MCPServer, MCPServerAppPermission
from apigateway.apps.permission.constants import GrantTypeEnum
from apigateway.apps.permission.models import AppResourcePermission
from apigateway.core.models import Resource
from apigateway.utils.time import NeverExpiresTime


def _virtual_app_code(mcp_server_id: int, bk_app_code: str) -> str:
    return f"v_mcp_{mcp_server_id}_{bk_app_code}"


def _sync_new_resource_permissions(
    mcp_server: MCPServer,
    bk_app_codes: set[str],
    dry_run: bool,
) -> int:
    resource_names = mcp_server.resource_names
    if not resource_names:
        return 0

    resource_ids = set(
        Resource.objects.filter(
            gateway_id=mcp_server.gateway_id,
            name__in=resource_names,
        ).values_list("id", flat=True)
    )
    expected_permission_keys = {
        (_virtual_app_code(mcp_server.id, bk_app_code), resource_id)
        for bk_app_code in bk_app_codes
        for resource_id in resource_ids
    }
    if not expected_permission_keys:
        return 0

    current_permission_keys = set(
        AppResourcePermission.objects.filter(
            gateway_id=mcp_server.gateway_id,
            bk_app_code__in={key[0] for key in expected_permission_keys},
            resource_id__in=resource_ids,
        ).values_list("bk_app_code", "resource_id")
    )
    permissions_to_add = [
        AppResourcePermission(
            bk_app_code=bk_app_code,
            gateway=mcp_server.gateway,
            resource_id=resource_id,
            expires=NeverExpiresTime.time,
            grant_type=GrantTypeEnum.SYNC.value,
        )
        for bk_app_code, resource_id in expected_permission_keys - current_permission_keys
    ]
    if permissions_to_add and not dry_run:
        AppResourcePermission.objects.bulk_create(permissions_to_add, ignore_conflicts=True)

    return len(permissions_to_add)


class Command(BaseCommand):
    help = """
    Import MCP server app permissions from CSV.

    Locate agent_code and mcp_code by the CSV header. agent_code is used as
    bk_app_code, and mcp_code is matched against MCPServer.name. Existing
    permissions are kept unchanged; only missing MCP and resource permissions
    are created.

    Example:
      python manage.py mcp_server_permission_import_csv --file=permissions.csv
      python manage.py mcp_server_permission_import_csv --file=permissions.csv --dry-run
    """

    def add_arguments(self, parser):
        parser.add_argument("--file", "-f", type=str, required=True, help="Input CSV file path")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and calculate changes without writing permissions",
        )

    def handle(self, *args, **options):  # noqa: C901, PLR0912, PLR0915
        file_path = options["file"]
        dry_run = options["dry_run"]
        created = 0
        existing = 0
        skipped = 0
        seen_pairs = set()
        new_app_codes_by_mcp_server_id: dict[int, set[str]] = defaultdict(set)
        mcp_servers: dict[str, MCPServer | None] = {}

        with transaction.atomic():
            with open(file_path, newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.reader(csv_file)
                try:
                    header = [value.strip() for value in next(reader)]
                except StopIteration as err:
                    raise CommandError("CSV header must contain agent_code and mcp_code") from err

                if "agent_code" not in header or "mcp_code" not in header:
                    raise CommandError("CSV header must contain agent_code and mcp_code")

                agent_code_column = header.index("agent_code")
                mcp_code_column = header.index("mcp_code")
                required_column = max(agent_code_column, mcp_code_column)

                for row_number, row in enumerate(reader, start=2):
                    if not row or not any(value.strip() for value in row):
                        continue
                    if len(row) <= required_column:
                        self.stderr.write(
                            f"warning: row={row_number} does not contain agent_code/mcp_code columns, skip"
                        )
                        skipped += 1
                        continue

                    agent_code = row[agent_code_column].strip()
                    mcp_code = row[mcp_code_column].strip()
                    if not agent_code or not mcp_code:
                        self.stderr.write(f"warning: row={row_number} has empty agent_code/mcp_code, skip")
                        skipped += 1
                        continue

                    permission_key = (agent_code, mcp_code)
                    if permission_key in seen_pairs:
                        skipped += 1
                        continue
                    seen_pairs.add(permission_key)

                    if mcp_code not in mcp_servers:
                        mcp_servers[mcp_code] = MCPServer.objects.filter(name=mcp_code).first()
                    mcp_server = mcp_servers[mcp_code]
                    if mcp_server is None:
                        self.stderr.write(f"warning: row={row_number} mcp_code={mcp_code!r} not found, skip")
                        skipped += 1
                        continue

                    if dry_run:
                        self.stdout.write(
                            f"Dry run permission: bk_app_code={agent_code!r}, mcp_server_name={mcp_server.name!r}"
                        )
                        created_flag = not MCPServerAppPermission.objects.filter(
                            bk_app_code=agent_code,
                            mcp_server=mcp_server,
                        ).exists()
                    else:
                        _, created_flag = MCPServerAppPermission.objects.get_or_create(
                            bk_app_code=agent_code,
                            mcp_server=mcp_server,
                            defaults={
                                "grant_type": MCPServerAppPermissionGrantTypeEnum.GRANT.value,
                                "expires": NeverExpiresTime.time,
                            },
                        )
                    if not created_flag:
                        existing += 1
                        continue

                    created += 1
                    new_app_codes_by_mcp_server_id[mcp_server.id].add(agent_code)

            synced_resource_permissions = 0
            mcp_servers_by_id = {
                mcp_server.id: mcp_server for mcp_server in mcp_servers.values() if mcp_server is not None
            }
            for mcp_server_id, agent_codes in new_app_codes_by_mcp_server_id.items():
                synced_resource_permissions += _sync_new_resource_permissions(
                    mcp_servers_by_id[mcp_server_id],
                    agent_codes,
                    dry_run,
                )

        result_prefix = "Dry run done" if dry_run else "Import done"
        self.stdout.write(
            self.style.SUCCESS(
                f"{result_prefix}: "
                f"created={created}, existing={existing}, skipped={skipped}, "
                f"synced_mcp_servers={len(new_app_codes_by_mcp_server_id)}, "
                f"synced_resource_permissions={synced_resource_permissions}"
            )
        )
