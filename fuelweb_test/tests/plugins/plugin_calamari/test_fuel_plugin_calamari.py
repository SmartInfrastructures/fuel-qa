#    Copyright 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os

from proboscis.asserts import assert_equal, assert_true
from proboscis import test

from fuelweb_test import logger
from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test.helpers import checkers
from fuelweb_test.helpers import utils
from fuelweb_test.settings import DEPLOYMENT_MODE
from fuelweb_test.settings import CALAMARI_PLUGIN_PATH
from fuelweb_test.tests.base_test_case import SetupEnvironment
from fuelweb_test.tests.base_test_case import TestBasic


@test(groups=["fuel_plugins"])
class CalamariPlugin(TestBasic):
    """CalamariPlugin."""  # TODO documentation

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["deploy_ha_controller_neutron_calamari"])
    @log_snapshot_after_test
    def deploy_ha_one_controller_neutron_calamari(self):
        """Deploy cluster with one controller and calamari plugin

        Scenario:
            1. Upload plugin to the master node
            2. Install plugin
            3. Create cluster
            4. Add 1 node with controller role
            5. Add 2 nodes with compute role with ceph
            5. Add 1 node with calamari name
            6. Deploy the cluster
            7. Run network verification
            8. Check plugin health
            9. Run OSTF

        Duration 35m TODO
        Snapshot deploy_ha_one_controller_neutron_calamari
        """
        checkers.check_plugin_path_env(
            var_name='CALAMARI_PLUGIN_PATH',
            plugin_path=CALAMARI_PLUGIN_PATH
        )
        
        self.env.revert_snapshot("ready_with_5_slaves")

        # copy plugin to the master node
        checkers.check_archive_type(CALAMARI_PLUGIN_PATH)
        
        utils.upload_tarball(
            ip=self.ssh_manager.admin_ip,
            tar_path=CALAMARI_PLUGIN_PATH,
            tar_target='/var'
        )

        # install plugin

        utils.install_plugin_check_code(
            ip=self.ssh_manager.admin_ip,
            plugin=os.path.basename(CALAMARI_PLUGIN_PATH))

        segment_type = NEUTRON_SEGMENT['vlan']
        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=DEPLOYMENT_MODE,
            settings={
                "net_provider": 'neutron',
                "net_segment_type": segment_type,
                "propagate_task_deploy": True
            }
        )

        plugin_name = 'fuel_plugin_calamari'
        msg = "Plugin couldn't be enabled. Check plugin version. Test aborted"
        assert_true(
            self.fuel_web.check_plugin_exists(cluster_id, plugin_name),
            msg)
        options = {'metadata/enabled': True}
        self.fuel_web.update_plugin_data(cluster_id, plugin_name, options)

        self.fuel_web.update_nodes(
            cluster_id,
            {
                'slave-01': ['controller'],
                'slave-02': ['compute', 'ceph-osd'],
                'slave-03': ['compute', 'ceph-osd'],
                'slave-04': ['base-os'],
            }
        )
        self.fuel_web.deploy_cluster_wait(cluster_id)

        self.fuel_web.verify_network(cluster_id)

        # check if service ran on controller
        logger.debug("Start to check service on node {0}".format('slave-01'))
        cmd_curl = 'curl localhost:8234'
        cmd = 'pgrep -f fuel-simple-service'

        _ip = self.fuel_web.get_nailgun_node_by_name("slave-01")['ip']
        res_pgrep = self.env.d_env.get_ssh_to_remote(_ip).execute(cmd)
        assert_equal(0, res_pgrep['exit_code'],
                     'Failed with error {0}'.format(res_pgrep['stderr']))
        assert_equal(1, len(res_pgrep['stdout']),
                     'Failed with error {0}'.format(res_pgrep['stderr']))
        # curl to service
        _ip = self.fuel_web.get_nailgun_node_by_name("slave-01")['ip']
        res_curl = self.env.d_env.get_ssh_to_remote(_ip).execute(cmd_curl)
        assert_equal(0, res_pgrep['exit_code'],
                     'Failed with error {0}'.format(res_curl['stderr']))

        self.fuel_web.run_ostf(
            cluster_id=cluster_id)

        self.env.make_snapshot("deploy_ha_one_controller_neutron_calamari")

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["deploy_nova_calamari_ha"])
    @log_snapshot_after_test
    def deploy_nova_calamari_ha(self):
        """Deploy cluster in ha mode with calamari plugin

        Scenario:
            1. Upload plugin to the master node
            2. Install plugin
            3. Create cluster
            4. Add 3 node with controller role
            5. Add 1 nodes with compute role
            6. Add 1 nodes with cinder role
            7. Deploy the cluster
            8. Run network verification
            9. check plugin health
            10. Run OSTF

        Duration 70m
        Snapshot deploy_nova_calamari_ha

        """
        checkers.check_plugin_path_env(
            var_name='CALAMARI_PLUGIN_PATH',
            plugin_path=CALAMARI_PLUGIN_PATH
        )
                
        self.env.revert_snapshot("ready_with_5_slaves")

        # copy plugin to the master node
        checkers.check_archive_type(CALAMARI_PLUGIN_PATH)

        utils.upload_tarball(
            ip=self.ssh_manager.admin_ip,
            tar_path=CALAMARI_PLUGIN_PATH,
            tar_target='/var'
        )

        # install plugin

        utils.install_plugin_check_code(
            ip=self.ssh_manager.admin_ip,
            plugin=os.path.basename(CALAMARI_PLUGIN_PATH))


        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=DEPLOYMENT_MODE,
            settings={"propagate_task_deploy": True}
        )

        plugin_name = 'fuel_plugin_calamari'
        msg = "Plugin couldn't be enabled. Check plugin version. Test aborted"
        assert_true(
            self.fuel_web.check_plugin_exists(cluster_id, plugin_name),
            msg)
        options = {'metadata/enabled': True}
        self.fuel_web.update_plugin_data(cluster_id, plugin_name, options)

        self.fuel_web.update_nodes(
            cluster_id,
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute'],
                'slave-05': ['cinder']
            }
        )
        self.fuel_web.deploy_cluster_wait(cluster_id)
        self.fuel_web.verify_network(cluster_id)

        for node in ('slave-01', 'slave-02', 'slave-03'):
            logger.debug("Start to check service on node {0}".format(node))
            cmd_curl = 'curl localhost:8234'
            cmd = 'pgrep -f fuel-simple-service'
            _ip = self.fuel_web.get_nailgun_node_by_name(node)['ip']
            res_pgrep = self.env.d_env.get_ssh_to_remote(_ip).execute(cmd)
            assert_equal(0, res_pgrep['exit_code'],
                         'Failed with error {0} '
                         'on node {1}'.format(res_pgrep['stderr'], node))
            assert_equal(1, len(res_pgrep['stdout']),
                         'Failed with error {0} on the '
                         'node {1}'.format(res_pgrep['stderr'], node))
            # curl to service
            _ip = self.fuel_web.get_nailgun_node_by_name(node)['ip']
            res_curl = self.env.d_env.get_ssh_to_remote(_ip).execute(cmd_curl)
            assert_equal(0, res_pgrep['exit_code'],
                         'Failed with error {0} '
                         'on node {1}'.format(res_curl['stderr'], node))

        self.fuel_web.run_ostf(
            cluster_id=cluster_id)

        self.env.make_snapshot("deploy_nova_calamari_ha")

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["deploy_neutron_calamari_ha_add_node"])
    @log_snapshot_after_test
    def deploy_neutron_calamari_ha_add_node(self):
        """Deploy and scale cluster in ha mode with calamari plugin

        Scenario:
            1. Upload plugin to the master node
            2. Install plugin
            3. Create cluster
            4. Add 1 node with controller role
            5. Add 1 nodes with compute role
            6. Add 1 nodes with cinder role
            7. Deploy the cluster
            8. Run network verification
            9. Check plugin health
            10. Add 2 nodes with controller role
            11. Deploy cluster
            12. Check plugin health
            13. Run OSTF

        Duration 150m
        Snapshot deploy_neutron_calamari_ha_add_node

        """
        checkers.check_plugin_path_env(
            var_name='CALAMARI_PLUGIN_PATH',
            plugin_path=CALAMARI_PLUGIN_PATH
        )
        
        self.env.revert_snapshot("ready_with_5_slaves")

        # copy plugin to the master node

        utils.upload_tarball(
            ip=self.ssh_manager.admin_ip,
            tar_path=CALAMARI_PLUGIN_PATH,
            tar_target='/var'
        )

        # install plugin

        utils.install_plugin_check_code(
            ip=self.ssh_manager.admin_ip,
            plugin=os.path.basename(CALAMARI_PLUGIN_PATH))

        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=DEPLOYMENT_MODE,
            settings={
                "net_provider": 'neutron',
                "net_segment_type": NEUTRON_SEGMENT['tun'],
                "propagate_task_deploy": True
            }
        )


        plugin_name = 'fuel_plugin_calamari'
        msg = "Plugin couldn't be enabled. Check plugin version. Test aborted"
        assert_true(
            self.fuel_web.check_plugin_exists(cluster_id, plugin_name),
            msg)
        options = {'metadata/enabled': True}
        self.fuel_web.update_plugin_data(cluster_id, plugin_name, options)

        self.fuel_web.update_nodes(
            cluster_id,
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': ['compute', ceph]
            }
        )
        self.fuel_web.deploy_cluster_wait(cluster_id)
        self.fuel_web.verify_network(cluster_id)
        
        # TODO: ADD test here

        # add verification here
        self.fuel_web.run_ostf(
            cluster_id=cluster_id)

        self.env.make_snapshot("deploy_neutron_calamari_ha_add_node")
