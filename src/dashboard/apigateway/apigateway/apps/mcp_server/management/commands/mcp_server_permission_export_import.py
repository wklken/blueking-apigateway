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
import json
from typing import TYPE_CHECKING, Iterable, Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apigateway.apps.mcp_server.constants import MCPServerAppPermissionGrantTypeEnum
from apigateway.apps.mcp_server.models import MCPServer, MCPServerAppPermission
from apigateway.apps.permission.constants import GrantTypeEnum
from apigateway.apps.permission.models import AppResourcePermission
from apigateway.core.models import Resource
from apigateway.utils.time import NeverExpiresTime

if TYPE_CHECKING:
    import datetime


def _parse_names(value: str) -> list[str]:
    names: list[str] = []
    for raw_item in value.split(","):
        name = raw_item.strip()
        if name:
            names.append(name)
    return names


def _read_mcp_server_names(file_path: str) -> list[str]:
    names: list[str] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:
                names.append(name)
    return names


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _virtual_app_code_prefix(mcp_server_id: int) -> str:
    return f"v_mcp_{mcp_server_id}_"


def _virtual_app_code(mcp_server_id: int, app_code: str) -> str:
    return f"v_mcp_{mcp_server_id}_{app_code}"


def _save_mcp_server_permission(
    mcp_server_id: int,
    bk_app_code: str,
    grant_type: str,
    expires: Optional["datetime.datetime"],
) -> None:
    MCPServerAppPermission.objects.update_or_create(
        bk_app_code=bk_app_code,
        mcp_server_id=mcp_server_id,
        defaults={
            "grant_type": grant_type,
            "expires": expires,
        },
    )


def _sync_resource_permissions(mcp_server_id: int) -> None:
    mcp_server = MCPServer.objects.get(id=mcp_server_id)

    public_app_code = settings.MCP_SERVER_OAUTH2_PUBLIC_CLIENT_APP_CODE
    if mcp_server.oauth2_public_client_enabled:
        _save_mcp_server_permission(
            mcp_server_id=mcp_server_id,
            bk_app_code=public_app_code,
            grant_type=MCPServerAppPermissionGrantTypeEnum.GRANT.value,
            expires=NeverExpiresTime.time,
        )
    else:
        MCPServerAppPermission.objects.filter(
            mcp_server_id=mcp_server_id,
            bk_app_code=public_app_code,
        ).delete()

    app_codes = list(
        MCPServerAppPermission.objects.filter(mcp_server=mcp_server).values_list("bk_app_code", flat=True)
    )
    if not app_codes:
        AppResourcePermission.objects.filter(
            gateway_id=mcp_server.gateway_id,
            bk_app_code__startswith=_virtual_app_code_prefix(mcp_server_id),
        ).delete()
        return

    resource_names = mcp_server.resource_names
    if not resource_names:
        return

    resource_ids = list(
        Resource.objects.filter(gateway_id=mcp_server.gateway_id, name__in=resource_names).values_list("id", flat=True)
    )
    newest_permission_keys = {
        (_virtual_app_code(mcp_server_id, app_code), resource_id)
        for app_code in app_codes
        for resource_id in resource_ids
    }

    current_permissions = AppResourcePermission.objects.filter(
        gateway_id=mcp_server.gateway_id,
        bk_app_code__startswith=_virtual_app_code_prefix(mcp_server_id),
    )
    current_permission_keys = {(permission.bk_app_code, permission.resource_id) for permission in current_permissions}

    if newest_permission_keys == current_permission_keys:
        return

    permissions_to_add = [
        AppResourcePermission(
            bk_app_code=virtual_app_code,
            gateway=mcp_server.gateway,
            resource_id=resource_id,
            expires=NeverExpiresTime.time,
            grant_type=GrantTypeEnum.SYNC.value,
        )
        for virtual_app_code, resource_id in newest_permission_keys - current_permission_keys
    ]
    permission_ids_to_delete = [
        permission.id
        for permission in current_permissions
        if (permission.bk_app_code, permission.resource_id) in current_permission_keys - newest_permission_keys
    ]

    if permissions_to_add:
        AppResourcePermission.objects.bulk_create(permissions_to_add)
    if permission_ids_to_delete:
        AppResourcePermission.objects.filter(id__in=permission_ids_to_delete).delete()


class Command(BaseCommand):
    help = """
    Export/import MCPServerAppPermission records by bk_app_code and mcp_server_name.

    Export: read MCP server names from --mcp-server-names-file and write permissions to JSON.
    Import: read JSON records and upsert permissions by mcp_server_name, always using
            grant_type=grant and expires=2100-01-01T00:00:00+00:00, then sync permissions
            to permission_app_resource.

    File format:
    [
      {
        "bk_app_code": "app-code",
        "mcp_server_name": "gateway-prod-demo"
      }
    ]

    Examples:
      python manage.py mcp_server_permission_export_import export --mcp-server-names-file=mcp_names.txt --file=perms.json
      python manage.py mcp_server_permission_export_import import --file=perms.json
    """

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["export", "import"])
        parser.add_argument(
            "--file", "-f", type=str, required=True, help="Output path for export, input path for import"
        )
        parser.add_argument(
            "--mcp-server-names-file",
            type=str,
            default="",
            help="MCP server name list file, one name per line. Used by export and as optional import filter.",
        )
        parser.add_argument(
            "--mcp-server-names",
            type=str,
            default="",
            help="Comma-separated MCP server names. Used by export and as optional import filter.",
        )

    def _get_mcp_server_names(self, mcp_server_names_file: str, mcp_server_names: str) -> list[str]:
        names = []
        if mcp_server_names_file:
            names.extend(_read_mcp_server_names(mcp_server_names_file))
        if mcp_server_names:
            names.extend(_parse_names(mcp_server_names))
        return _dedupe_keep_order(names)

    def _export(self, file_path: str, mcp_server_names: list[str]) -> None:
        if mcp_server_names:
            queryset = MCPServer.objects.filter(name__in=mcp_server_names).order_by("name")
            existing_names = set(queryset.values_list("name", flat=True))
            for missing_name in mcp_server_names:
                if missing_name not in existing_names:
                    self.stderr.write(f"warning: mcp_server_name={missing_name!r} not found, skip")
        else:
            queryset = MCPServer.objects.all().order_by("name")

        permissions = (
            MCPServerAppPermission.objects.filter(mcp_server__in=queryset)
            .select_related("mcp_server")
            .order_by("mcp_server__name", "bk_app_code")
        )
        records = [
            {
                "bk_app_code": permission.bk_app_code,
                "mcp_server_name": permission.mcp_server.name,
            }
            for permission in permissions
        ]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"Exported {len(records)} records to {file_path}"))

    def _import(self, file_path: str, mcp_server_names: list[str]) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stderr.write("error: file must contain a JSON array")
            return

        name_filter = set(mcp_server_names)
        created = 0
        updated = 0
        skipped = 0
        changed_mcp_server_ids = set()

        with transaction.atomic():
            for index, record in enumerate(data):
                if not isinstance(record, dict):
                    self.stderr.write(f"error: record at index {index} is not an object, skip")
                    skipped += 1
                    continue

                bk_app_code = record.get("bk_app_code")
                mcp_server_name = record.get("mcp_server_name")
                if not bk_app_code or not mcp_server_name:
                    self.stderr.write(f"error: record at index {index} missing bk_app_code/mcp_server_name, skip")
                    skipped += 1
                    continue

                if name_filter and mcp_server_name not in name_filter:
                    skipped += 1
                    continue

                mcp_server = MCPServer.objects.filter(name=mcp_server_name).first()
                if not mcp_server:
                    self.stderr.write(f"warning: mcp_server_name={mcp_server_name!r} not found, skip")
                    skipped += 1
                    continue

                _, created_flag = MCPServerAppPermission.objects.update_or_create(
                    bk_app_code=bk_app_code,
                    mcp_server=mcp_server,
                    defaults={
                        "grant_type": MCPServerAppPermissionGrantTypeEnum.GRANT.value,
                        "expires": NeverExpiresTime.time,
                    },
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
                changed_mcp_server_ids.add(mcp_server.id)

            for mcp_server_id in sorted(changed_mcp_server_ids):
                _sync_resource_permissions(mcp_server_id)

        self.stdout.write(
            self.style.SUCCESS(
                "Import done: "
                f"created={created}, updated={updated}, skipped={skipped}, synced={len(changed_mcp_server_ids)}"
            )
        )

    def handle(self, action, file, mcp_server_names_file, mcp_server_names, **options):
        names = self._get_mcp_server_names(mcp_server_names_file, mcp_server_names)
        if action == "export":
            self._export(file, names)
            return

        self._import(file, names)
