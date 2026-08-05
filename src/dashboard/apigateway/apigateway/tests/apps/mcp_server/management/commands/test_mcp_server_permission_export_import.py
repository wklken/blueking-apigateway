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

import pytest
from ddf import G

from apigateway.apps.mcp_server.constants import MCPServerAppPermissionGrantTypeEnum
from apigateway.apps.mcp_server.management.commands.mcp_server_permission_export_import import Command
from apigateway.apps.mcp_server.models import MCPServer, MCPServerAppPermission
from apigateway.apps.permission.constants import GrantTypeEnum
from apigateway.apps.permission.models import AppResourcePermission
from apigateway.core.models import Resource
from apigateway.utils.time import NeverExpiresTime

pytestmark = pytest.mark.django_db


class TestCommand:
    def test_export_permissions_by_mcp_server_name_file(self, fake_gateway, fake_stage, tmp_path):
        mcp_server = G(
            MCPServer,
            gateway=fake_gateway,
            stage=fake_stage,
            name="server-a",
        )
        G(
            MCPServerAppPermission,
            mcp_server=mcp_server,
            bk_app_code="app-a",
            grant_type=MCPServerAppPermissionGrantTypeEnum.GRANT.value,
            expires=NeverExpiresTime.time,
        )
        G(
            MCPServerAppPermission,
            mcp_server=mcp_server,
            bk_app_code="app-b",
            grant_type=MCPServerAppPermissionGrantTypeEnum.APPLY.value,
            expires=NeverExpiresTime.time,
        )
        other_mcp_server = G(
            MCPServer,
            gateway=fake_gateway,
            stage=fake_stage,
            name="server-b",
        )
        G(
            MCPServerAppPermission,
            mcp_server=other_mcp_server,
            bk_app_code="app-c",
            grant_type=MCPServerAppPermissionGrantTypeEnum.GRANT.value,
            expires=NeverExpiresTime.time,
        )
        name_file = tmp_path / "mcp_names.txt"
        output_file = tmp_path / "permissions.json"
        name_file.write_text("server-a\nmissing-server\n", encoding="utf-8")

        Command().handle(
            action="export",
            file=str(output_file),
            mcp_server_names_file=str(name_file),
            mcp_server_names="",
        )

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert data == [
            {
                "bk_app_code": "app-a",
                "mcp_server_name": "server-a",
            },
            {
                "bk_app_code": "app-b",
                "mcp_server_name": "server-a",
            },
        ]

    def test_import_permissions_by_name_and_syncs_resource_permissions(
        self,
        fake_gateway,
        fake_stage,
        fake_resource,
        tmp_path,
    ):
        mcp_server = G(
            MCPServer,
            gateway=fake_gateway,
            stage=fake_stage,
            name="server-a",
        )
        mcp_server.update_resource_names([fake_resource.name], [fake_resource.name])
        mcp_server.save(update_fields=["_resource_names"])
        input_file = tmp_path / "permissions.json"
        input_file.write_text(
            json.dumps(
                [
                    {
                        "bk_app_code": "app-a",
                        "mcp_server_name": "server-a",
                        "grant_type": MCPServerAppPermissionGrantTypeEnum.APPLY.value,
                        "expires": "invalid-expires-should-be-ignored",
                    },
                    {
                        "bk_app_code": "app-missing",
                        "mcp_server_name": "missing-server",
                        "grant_type": "invalid-grant-type-should-be-ignored",
                        "expires": "invalid-expires-should-be-ignored",
                    },
                ]
            ),
            encoding="utf-8",
        )

        Command().handle(
            action="import",
            file=str(input_file),
            mcp_server_names_file="",
            mcp_server_names="",
        )

        permission = MCPServerAppPermission.objects.get(mcp_server=mcp_server, bk_app_code="app-a")
        assert permission.grant_type == MCPServerAppPermissionGrantTypeEnum.GRANT.value
        assert permission.expires == NeverExpiresTime.time
        assert not MCPServerAppPermission.objects.filter(bk_app_code="app-missing").exists()
        assert AppResourcePermission.objects.filter(
            gateway=fake_gateway,
            bk_app_code=f"v_mcp_{mcp_server.id}_app-a",
            resource_id=fake_resource.id,
            grant_type=GrantTypeEnum.SYNC.value,
        ).exists()

    def test_import_updates_by_mcp_server_name_not_old_id_and_removes_stale_resource_permissions(
        self,
        fake_gateway,
        fake_stage,
        fake_resource,
        tmp_path,
    ):
        mcp_server = G(
            MCPServer,
            gateway=fake_gateway,
            stage=fake_stage,
            name="server-a",
        )
        mcp_server.update_resource_names([fake_resource.name], [fake_resource.name])
        mcp_server.save(update_fields=["_resource_names"])
        stale_resource = G(Resource, gateway=fake_gateway, name="stale-resource")
        existing_permission = G(
            MCPServerAppPermission,
            mcp_server=mcp_server,
            bk_app_code="app-a",
            grant_type=MCPServerAppPermissionGrantTypeEnum.GRANT.value,
            expires=NeverExpiresTime.time,
        )
        stale_virtual_app_code = f"v_mcp_{mcp_server.id}_old-app"
        G(
            AppResourcePermission,
            gateway=fake_gateway,
            bk_app_code=stale_virtual_app_code,
            resource_id=stale_resource.id,
            expires=NeverExpiresTime.time,
            grant_type=GrantTypeEnum.SYNC.value,
        )
        input_file = tmp_path / "permissions.json"
        input_file.write_text(
            json.dumps(
                [
                    {
                        "mcp_server_id": 999999,
                        "bk_app_code": "app-a",
                        "mcp_server_name": "server-a",
                        "grant_type": MCPServerAppPermissionGrantTypeEnum.APPLY.value,
                        "expires": "invalid-expires-should-be-ignored",
                    }
                ]
            ),
            encoding="utf-8",
        )

        Command().handle(
            action="import",
            file=str(input_file),
            mcp_server_names_file="",
            mcp_server_names="",
        )

        existing_permission.refresh_from_db()
        assert existing_permission.grant_type == MCPServerAppPermissionGrantTypeEnum.GRANT.value
        assert not AppResourcePermission.objects.filter(bk_app_code=stale_virtual_app_code).exists()
        assert AppResourcePermission.objects.filter(
            gateway=fake_gateway,
            bk_app_code=f"v_mcp_{mcp_server.id}_app-a",
            resource_id=fake_resource.id,
        ).exists()
