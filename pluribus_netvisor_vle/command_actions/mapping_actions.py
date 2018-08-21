import re
from copy import copy

import pluribus_netvisor_vle.command_templates.mapping as command_template
from cloudshell.cli.command_template.command_template_executor import CommandTemplateExecutor
from pluribus_netvisor_vle.command_actions.actions_helper import ActionsHelper


class MappingActions(object):
    PORTS = 'ports'
    BIDIR = 'bidir'
    MONITOR_PORTS = 'monitor_ports'

    """
    Autoload actions
    """

    def __init__(self, cli_service, logger):
        """
        :param logger:
        :type logger: Logger
        :return:
        """
        self._logger = logger
        self._cli_service = cli_service

        self.__associations_table = None
        self.__phys_to_logical_table = None

    @property
    def cli_service(self):
        return self._cli_service

    @cli_service.setter
    def cli_service(self, cli_service):
        self._cli_service = cli_service

    def map_bidi_multi_node(self, src_node, dst_node, src_port, dst_port, src_tunnel, dst_tunnel, vlan_id, vle_name):
        self._validate_port_is_not_a_member(src_node, src_port)
        self._validate_port_is_not_a_member(dst_node, dst_port)
        self._create_vlan(src_node, src_port, vlan_id)
        out = CommandTemplateExecutor(self._cli_service, command_template.ADD_VXLAN_TO_TUNNEL).execute_command(
            node_name=src_node, tunnel_name=src_tunnel, vxlan_id=vlan_id)
        self._validate_vxlan_add(src_node, vlan_id, src_tunnel)

        self._create_vlan(dst_node, dst_port, vlan_id)
        out += CommandTemplateExecutor(self._cli_service, command_template.ADD_VXLAN_TO_TUNNEL).execute_command(
            node_name=dst_node, tunnel_name=dst_tunnel, vxlan_id=vlan_id)
        self._validate_vxlan_add(dst_node, vlan_id, dst_tunnel)

        out += CommandTemplateExecutor(self._cli_service, command_template.VLE_CREATE).execute_command(
            vle_name=vle_name, node_1=src_node, node_1_port=src_port, node_2=dst_node, node_2_port=dst_port)
        self._validate_vle_creation(vle_name)

    def map_bidi_single_node(self, node, src_port, dst_port, vlan_id, vle_name):
        self._validate_port_is_not_a_member(node, src_port)
        self._validate_port_is_not_a_member(node, dst_port)
        self._create_vlan(node, src_port, vlan_id)
        self._add_to_vlan(node, dst_port, vlan_id)

        out = CommandTemplateExecutor(self._cli_service, command_template.VLE_CREATE).execute_command(
            vle_name=vle_name, node_1=node, node_1_port=src_port, node_2=node, node_2_port=dst_port)
        self._validate_vle_creation(vle_name)

    def delete_single_node_vle(self, node, vle_name, vlan_id):
        out = CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLE).execute_command(vle_name=vle_name)
        self._validate_vle_deletion(vle_name)
        out += CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLAN).execute_command(node=node,
                                                                                                        vlan_id=vlan_id)
        self._validate_vlan_id_deletion(node, vlan_id)

    def delete_multi_node_vle(self, src_node, dst_node, vle_name, vlan_id):
        out = CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLE).execute_command(vle_name=vle_name)
        self._validate_vle_deletion(vle_name)
        out += CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLAN).execute_command(node=src_node,
                                                                                                        vlan_id=vlan_id)
        self._validate_vlan_id_deletion(src_node, vlan_id)
        out += CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLAN).execute_command(node=dst_node,
                                                                                                        vlan_id=vlan_id)
        self._validate_vlan_id_deletion(dst_node, vlan_id)

    def connection_table(self):
        out = CommandTemplateExecutor(self._cli_service, command_template.VLE_SHOW,
                                      remove_prompt=True).execute_command()

        vle_name_key = 'vle_name'
        node_1_key = 'node_1'
        node_2_key = 'node_2'
        node_1_port_key = 'node_1_port'
        node_2_port_key = 'node_2_port'
        connection_table = {}
        out_table = ActionsHelper.parse_table_by_keys(out, vle_name_key, node_1_key, node_2_key, node_1_port_key,
                                                      node_2_port_key)
        for record in out_table:
            src_record = (record[node_1_key], record[node_1_port_key])
            dst_record = (record[node_2_key], record[node_2_port_key])
            vle_name = record[vle_name_key]
            connection_table[src_record] = (dst_record, vle_name)
            connection_table[dst_record] = (src_record, vle_name)
        return connection_table

    def _create_vlan(self, node, port, vlan_id):
        # self._validate_port_is_not_a_member(node, port)
        out = CommandTemplateExecutor(self._cli_service, command_template.CREATE_VLAN, ).execute_command(
            node_name=node, vlan_id=vlan_id, vxlan_id=vlan_id, port=port)
        self._validate_port_is_a_member(node, port, vlan_id)

    def _add_to_vlan(self, node, port, vlan_id):
        # self._validate_port_is_not_a_member(node, port)
        out = CommandTemplateExecutor(self._cli_service, command_template.ADD_TO_VLAN).execute_command(
            node_name=node, vlan_id=vlan_id, port=port)
        self._validate_port_is_a_member(node, port, vlan_id)

    def _validate_port_is_not_a_member(self, node, port):
        vlan_member = self.vlan_id_for_port(node, port)
        if vlan_member and vlan_member != 1:
            raise Exception(self.__class__.__name__,
                            'Port {} already a member of vlan_id {}'.format((node, port), vlan_member))

    def _validate_port_is_a_member(self, node, port, vlan_id):
        vlan_member = self.vlan_id_for_port(node, port)
        if not vlan_member or vlan_member != vlan_id:
            raise Exception(self.__class__.__name__, 'Cannot add port {} to vlan {}'.format((node, port), vlan_id))

    def _validate_vxlan_add(self, node_name, vxlan_id, tunnel):
        switch_key = 'switch'
        tunnel_name_key = 'tunnel_name'
        vxlan_id_key = 'vxlan_id'
        out = CommandTemplateExecutor(self._cli_service, command_template.VXLAN_SHOW,
                                      remove_prompt=True).execute_command(node_name=node_name, vxlan_id=vxlan_id)
        out_table = ActionsHelper.parse_table_by_keys(out, switch_key, tunnel_name_key, vxlan_id_key)
        active_tunnels = [record[tunnel_name_key] for record in out_table]
        if tunnel in active_tunnels:
            return
        raise Exception(self.__class__.__name__,
                        'Failed to add vxlan {} to tunnel {}, see driver logs for more details'.format(vxlan_id,
                                                                                                       tunnel))

    def _validate_vle_creation(self, vle_name):
        vle_name_key = 'vle_name'
        node_1_key = 'node_1'
        node_2_key = 'node_2'
        node_1_port_key = 'node_1_port'
        node_2_port_key = 'node_2_port'
        status_key = 'status'
        out = CommandTemplateExecutor(self._cli_service, command_template.VLE_SHOW_FOR_NAME,
                                      remove_prompt=True).execute_command(vle_name=vle_name)
        out_table = ActionsHelper.parse_table_by_keys(out, vle_name_key, node_1_key, node_1_port_key, node_2_key,
                                                      node_2_port_key, status_key)
        if not out_table or out_table[0].get(vle_name_key) != vle_name:
            raise Exception(self.__class__.__name__,
                            'VLE {} creation failed, see logs for more details'.format(vle_name))

    def _validate_vle_deletion(self, vle_name):
        vle_name_key = 'vle_name'
        node_1_key = 'node_1'
        node_2_key = 'node_2'
        node_1_port_key = 'node_1_port'
        node_2_port_key = 'node_2_port'
        status_key = 'status'
        out = CommandTemplateExecutor(self._cli_service, command_template.VLE_SHOW_FOR_NAME,
                                      remove_prompt=True).execute_command(vle_name=vle_name)
        out_table = ActionsHelper.parse_table_by_keys(out, vle_name_key, node_1_key, node_1_port_key, node_2_key,
                                                      node_2_port_key, status_key)
        if out_table:
            raise Exception(self.__class__.__name__,
                            'Failed to delete VLE {}, see logs for more details'.format(vle_name))

    def _validate_vlan_id_deletion(self, node_name, vlan_id):
        out = CommandTemplateExecutor(self._cli_service, command_template.VLAN_SHOW,
                                      remove_prompt=True).execute_command(node_name=node_name, vlan_id=vlan_id)
        vlan_id_key = 'vlan_id'
        switch_key = 'switch_key'
        vxlan_id_key = 'vxlan'
        out_table = ActionsHelper.parse_table_by_keys(out, vlan_id_key, switch_key, vxlan_id_key)
        if out_table:
            raise Exception(self.__class__.__name__, 'Failed to delete vlan {} on node {}'.format(vlan_id, node_name))

    def vlan_id_for_port(self, node, port):
        out = CommandTemplateExecutor(self._cli_service, command_template.PORT_VLAN_INFO,
                                      remove_prompt=True).execute_command(node=node, port=port)
        node_key = 'node'
        port_key = 'port'
        vlan_id_key = 'vlan'

        out_table = ActionsHelper.parse_table_by_keys(out, node_key, port_key, vlan_id_key)
        vlan_id = out_table[0].get(vlan_id_key)
        if vlan_id and vlan_id.lower() != 'none':
            return int(vlan_id)
