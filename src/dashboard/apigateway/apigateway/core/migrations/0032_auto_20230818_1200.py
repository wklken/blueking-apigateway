#
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - API 网关(BlueKing - APIGateway) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
# Generated by Django 3.2.18 on 2023-08-18 04:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_alter_publishevent_unique_together'),
    ]

    operations = [
        migrations.RenameField(
            model_name='microgateway',
            old_name='api',
            new_name='gateway',
        ),
        migrations.RenameField(
            model_name='microgatewayreleasehistory',
            old_name='api',
            new_name='gateway',
        ),
        migrations.RenameField(
            model_name='release',
            old_name='api',
            new_name='gateway',
        ),
        migrations.RenameField(
            model_name='releasedresource',
            old_name='api',
            new_name='gateway',
        ),
        migrations.RenameField(
            model_name='releasehistory',
            old_name='api',
            new_name='gateway',
        ),
        migrations.RenameField(
            model_name='resourceversion',
            old_name='api',
            new_name='gateway',
        ),
        migrations.AddField(
            model_name='releasehistory',
            name='source',
            field=models.CharField(choices=[('gateway_enable', '网关启用'), ('gateway_disable', '网关停用'), ('version_publish', '版本发布'), ('plugin_update', '插件更新'), ('plugin_bind', '插件绑定'), ('plugin_unbind', '插件解绑'), ('stage_disable', '环境下架'), ('stage_update', '环境更新'), ('stage_delete', '环境删除'), ('backend_update', '服务更新'), ('cli_sync', '命令行同步')], default='version_publish', max_length=64),
        ),
        migrations.AlterField(
            model_name='context',
            name='scope_type',
            field=models.CharField(choices=[('api', 'Gateway'), ('stage', 'Stage'), ('resource', 'Resource')], db_index=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='context',
            name='type',
            field=models.CharField(choices=[('api_auth', 'Gateway auth'), ('resource_auth', 'Resource auth'), ('stage_proxy_http', 'Stage proxy http'), ('stage_rate_limit', 'Stage rate limit'), ('api_feature_flag', 'Gateway feature flag')], max_length=32),
        ),
        migrations.AlterField(
            model_name='gateway',
            name='status',
            field=models.IntegerField(choices=[(0, '已停用'), (1, '启用中')]),
        ),
        migrations.AlterField(
            model_name='microgateway',
            name='gateway',
            field=models.ForeignKey(db_column='api_id', on_delete=django.db.models.deletion.PROTECT, to='core.gateway'),
        ),
        migrations.AlterField(
            model_name='microgatewayreleasehistory',
            name='gateway',
            field=models.ForeignKey(db_column='api_id', on_delete=django.db.models.deletion.CASCADE, to='core.gateway'),
        ),
        migrations.AlterField(
            model_name='publishevent',
            name='name',
            field=models.CharField(blank=True, choices=[('validata_configuration', 'validate configuration'), ('generate_release_task', 'generate release task'), ('distribute_configuration', 'distribute configuration'), ('parse_configuration', 'parse configuration'), ('apply_configuration', 'apply configuration'), ('load_configuration', 'load configuration')], max_length=64),
        ),
        migrations.AlterField(
            model_name='release',
            name='gateway',
            field=models.ForeignKey(db_column='api_id', on_delete=django.db.models.deletion.PROTECT, to='core.gateway'),
        ),
        migrations.AlterField(
            model_name='releasedresource',
            name='gateway',
            field=models.ForeignKey(db_column='api_id', on_delete=django.db.models.deletion.CASCADE, to='core.gateway'),
        ),
        migrations.AlterField(
            model_name='releasehistory',
            name='gateway',
            field=models.ForeignKey(db_column='api_id', on_delete=django.db.models.deletion.CASCADE, to='core.gateway'),
        ),
        migrations.AlterField(
            model_name='resourceversion',
            name='gateway',
            field=models.ForeignKey(db_column='api_id', on_delete=django.db.models.deletion.PROTECT, to='core.gateway'),
        ),
        migrations.AlterUniqueTogether(
            name='releasedresource',
            unique_together={('gateway', 'resource_version_id', 'resource_id')},
        ),
    ]
