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
import datetime
import io

import pytest
from ddf import G
from django.core.management import call_command
from django.core.management.base import CommandError

from apigateway.apps.mcp_server.constants import MCPServerAppPermissionGrantTypeEnum
from apigateway.apps.mcp_server.models import MCPServer, MCPServerAppPermission
from apigateway.apps.permission.constants import GrantTypeEnum
from apigateway.apps.permission.models import AppResourcePermission
from apigateway.utils.time import NeverExpiresTime

pytestmark = pytest.mark.django_db


class TestCommand:
    def test_import_is_additive_and_idempotent(
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

        original_expires = datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC)
        existing_permission = G(
            MCPServerAppPermission,
            mcp_server=mcp_server,
            bk_app_code="existing-agent",
            grant_type=MCPServerAppPermissionGrantTypeEnum.APPLY.value,
            expires=original_expires,
        )
        existing_resource_permission = G(
            AppResourcePermission,
            gateway=fake_gateway,
            bk_app_code=f"v_mcp_{mcp_server.id}_existing-agent",
            resource_id=fake_resource.id,
            grant_type=GrantTypeEnum.APPLY.value,
            expires=original_expires,
        )
        input_file = tmp_path / "permissions.csv"
        input_file.write_text(
            "agent_id,agent_code,agent_name,creator,published_at,publisher,mcp_code,mcp_name,mcp_id,"
            "gateway_id,gateway_name\n"
            "1,existing-agent,existing,creator,2026-07-28,publisher,server-a,Server A,1,1,gateway\n"
            "2,new-agent,new,creator,2026-07-28,publisher,server-a,Server A,1,1,gateway\n"
            "2,new-agent,new,creator,2026-07-28,publisher,server-a,Server A,1,1,gateway\n"
            "3,missing-agent,missing,creator,2026-07-28,publisher,missing-server,Missing,2,1,gateway\n"
            "invalid,short-row\n",
            encoding="utf-8",
        )

        call_command("mcp_server_permission_import_csv", file=str(input_file))
        call_command("mcp_server_permission_import_csv", file=str(input_file))

        existing_permission.refresh_from_db()
        existing_resource_permission.refresh_from_db()
        assert existing_permission.grant_type == MCPServerAppPermissionGrantTypeEnum.APPLY.value
        assert existing_permission.expires == original_expires
        assert existing_resource_permission.grant_type == GrantTypeEnum.APPLY.value
        assert existing_resource_permission.expires == original_expires

        new_permission = MCPServerAppPermission.objects.get(
            mcp_server=mcp_server,
            bk_app_code="new-agent",
        )
        assert new_permission.grant_type == MCPServerAppPermissionGrantTypeEnum.GRANT.value
        assert new_permission.expires == NeverExpiresTime.time
        assert AppResourcePermission.objects.filter(
            gateway=fake_gateway,
            bk_app_code=f"v_mcp_{mcp_server.id}_new-agent",
            resource_id=fake_resource.id,
            grant_type=GrantTypeEnum.SYNC.value,
            expires=NeverExpiresTime.time,
        ).exists()

        assert MCPServerAppPermission.objects.filter(mcp_server=mcp_server).count() == 2
        assert not MCPServerAppPermission.objects.filter(bk_app_code="missing-agent").exists()
        assert AppResourcePermission.objects.filter(gateway=fake_gateway).count() == 2

    def test_import_requires_agent_code_and_mcp_code_headers(self, tmp_path):
        input_file = tmp_path / "permissions.csv"
        input_file.write_text(
            "agent_id,agent_code,agent_name,creator\n1,agent-a,Agent A,creator\n",
            encoding="utf-8",
        )

        with pytest.raises(CommandError, match="agent_code and mcp_code"):
            call_command("mcp_server_permission_import_csv", file=str(input_file))

    def test_dry_run_does_not_create_permissions(
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
        input_file = tmp_path / "permissions.csv"
        input_file.write_text(
            "mcp_code,description,agent_code\n"
            "server-a,second permission,second-agent\n"
            "server-a,first permission,first-agent\n",
            encoding="utf-8",
        )

        stdout = io.StringIO()
        call_command(
            "mcp_server_permission_import_csv",
            file=str(input_file),
            dry_run=True,
            stdout=stdout,
        )

        permission_lines = [line for line in stdout.getvalue().splitlines() if line.startswith("Dry run permission:")]
        assert permission_lines == [
            "Dry run permission: bk_app_code='second-agent', mcp_server_name='server-a'",
            "Dry run permission: bk_app_code='first-agent', mcp_server_name='server-a'",
        ]
        assert "Dry run done: created=2" in stdout.getvalue()
        assert "synced_resource_permissions=2" in stdout.getvalue()
        assert not MCPServerAppPermission.objects.filter(
            mcp_server=mcp_server,
            bk_app_code__in=["second-agent", "first-agent"],
        ).exists()
        assert not AppResourcePermission.objects.filter(
            gateway=fake_gateway,
            bk_app_code__in=[
                f"v_mcp_{mcp_server.id}_second-agent",
                f"v_mcp_{mcp_server.id}_first-agent",
            ],
        ).exists()
