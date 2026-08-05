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

from unittest.mock import call, patch

import pytest
from ddf import G
from django.core.management.base import CommandError

from apigateway.apps.data_plane.management.commands.retry_undeploy_data_plane_gateways import (
    Command as RetryUndeployCommand,
)
from apigateway.apps.data_plane.models import DataPlane, GatewayDataPlaneBinding
from apigateway.controller.constants import DELETE_PUBLISH_ID
from apigateway.core.models import Gateway, Release, Stage

pytestmark = pytest.mark.django_db


@patch("apigateway.apps.data_plane.management.commands.retry_undeploy_data_plane_gateways.revoke_release")
def test_retry_unbound_gateway_retriggers_all_releases(mock_revoke_release, tmp_path):
    mock_revoke_release.return_value = True
    data_plane = G(DataPlane, name="default")
    gateway = G(Gateway, name="gw-a")
    release_prod = G(Release, gateway=gateway, stage=G(Stage, gateway=gateway, name="prod"))
    release_stag = G(Release, gateway=gateway, stage=G(Stage, gateway=gateway, name="stag"))
    names_file = tmp_path / "gateways.txt"
    names_file.write_text(f"{gateway.name}\n")

    RetryUndeployCommand().handle(
        gateway_names="",
        gateway_names_file=str(names_file),
        data_plane_name=data_plane.name,
        log_file=str(tmp_path / "retry.log"),
        operator="tester",
        dry_run=False,
        interval_seconds=0,
    )

    assert mock_revoke_release.call_args_list == [
        call(
            release_id=release_prod.id,
            publish_id=DELETE_PUBLISH_ID,
            data_plane_id=data_plane.id,
        ),
        call(
            release_id=release_stag.id,
            publish_id=DELETE_PUBLISH_ID,
            data_plane_id=data_plane.id,
        ),
    ]
    assert not GatewayDataPlaneBinding.objects.filter(gateway=gateway, data_plane=data_plane).exists()
    log_content = (tmp_path / "retry.log").read_text()
    assert '"action": "retry_undeploy_data_plane_gateway"' in log_content
    assert '"operator": "tester"' in log_content
    assert '"result": "success"' in log_content


@patch("apigateway.apps.data_plane.management.commands.retry_undeploy_data_plane_gateways.revoke_release")
def test_retry_rebound_gateway_rejects_whole_batch(mock_revoke_release, tmp_path):
    data_plane = G(DataPlane, name="default")
    unbound_gateway = G(Gateway, name="gw-a")
    rebound_gateway = G(Gateway, name="gw-b")
    G(Release, gateway=unbound_gateway, stage=G(Stage, gateway=unbound_gateway, name="prod"))
    G(Release, gateway=rebound_gateway, stage=G(Stage, gateway=rebound_gateway, name="prod"))
    G(GatewayDataPlaneBinding, gateway=rebound_gateway, data_plane=data_plane)

    with pytest.raises(CommandError, match="still bound to data plane"):
        RetryUndeployCommand().handle(
            gateway_names=f"{unbound_gateway.name},{rebound_gateway.name}",
            gateway_names_file="",
            data_plane_name=data_plane.name,
            log_file=str(tmp_path / "retry.log"),
            operator="tester",
            dry_run=False,
            interval_seconds=0,
        )

    mock_revoke_release.assert_not_called()


@patch("apigateway.apps.data_plane.management.commands.retry_undeploy_data_plane_gateways.revoke_release")
def test_retry_gateway_without_releases_is_logged_and_skipped(mock_revoke_release, tmp_path):
    mock_revoke_release.return_value = True
    data_plane = G(DataPlane, name="default")
    gateway_without_release = G(Gateway, name="gw-without-release")
    gateway_with_release = G(Gateway, name="gw-with-release")
    release = G(
        Release,
        gateway=gateway_with_release,
        stage=G(Stage, gateway=gateway_with_release, name="prod"),
    )
    log_file = tmp_path / "retry.log"

    RetryUndeployCommand().handle(
        gateway_names=f"{gateway_without_release.name},{gateway_with_release.name}",
        gateway_names_file="",
        data_plane_name=data_plane.name,
        log_file=str(log_file),
        operator="tester",
        dry_run=False,
        interval_seconds=0,
    )

    mock_revoke_release.assert_called_once_with(
        release_id=release.id,
        publish_id=DELETE_PUBLISH_ID,
        data_plane_id=data_plane.id,
    )
    log_content = log_file.read_text()
    assert f'"gateway_name": "{gateway_without_release.name}"' in log_content
    assert '"result": "skipped"' in log_content
    assert '"reason": "no_releases"' in log_content


@patch("apigateway.apps.data_plane.management.commands.retry_undeploy_data_plane_gateways.time.sleep")
@patch("apigateway.apps.data_plane.management.commands.retry_undeploy_data_plane_gateways.revoke_release")
def test_retry_throttles_each_release_at_default_interval(mock_revoke_release, mock_sleep, tmp_path):
    mock_revoke_release.return_value = True
    data_plane = G(DataPlane, name="default")
    gateway = G(Gateway, name="gw-a")
    G(Release, gateway=gateway, stage=G(Stage, gateway=gateway, name="prod"))
    G(Release, gateway=gateway, stage=G(Stage, gateway=gateway, name="stag"))

    RetryUndeployCommand().handle(
        gateway_names=gateway.name,
        gateway_names_file="",
        data_plane_name=data_plane.name,
        log_file=str(tmp_path / "retry.log"),
        operator="tester",
        dry_run=False,
    )

    assert mock_sleep.call_args_list == [call(60), call(60)]
