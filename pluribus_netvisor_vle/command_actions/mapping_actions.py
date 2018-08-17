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

    def map_bidi_multi_node(self, src_node, dst_node, src_port, dst_port, src_tunnel, dst_tunnel, vlan_id, vxlan_id,
                            vle_name):
        out = CommandTemplateExecutor(self._cli_service, command_template.CREATE_VLAN, ).execute_command(
            node_name=src_node, vlan_id=vlan_id, vxlan_id=vxlan_id, port=src_port)
        out += CommandTemplateExecutor(self._cli_service, command_template.ADD_VXLAN_TO_TUNNEL).execute_command(
            node_name=src_node, tunnel_name=src_tunnel, vxlan_id=vxlan_id)

        out = CommandTemplateExecutor(self._cli_service, command_template.CREATE_VLAN, ).execute_command(
            node_name=dst_node, vlan_id=vlan_id, vxlan_id=vxlan_id, port=dst_port)
        out += CommandTemplateExecutor(self._cli_service, command_template.ADD_VXLAN_TO_TUNNEL).execute_command(
            node_name=dst_node, tunnel_name=dst_tunnel, vxlan_id=vxlan_id)

        out += CommandTemplateExecutor(self._cli_service, command_template.VLE_CREATE).execute_command(
            vle_name=vle_name, node_1=src_node, node_1_port=src_port, node_2=dst_node, node_2_port=dst_port)

    def map_bidi_single_node(self, node, src_port, dst_port, vlan_id, vxlan_id, vle_name):
        out = CommandTemplateExecutor(self._cli_service, command_template.CREATE_VLAN, ).execute_command(
            node_name=node, vlan_id=vlan_id, vxlan_id=vxlan_id, port=src_port)
        out += CommandTemplateExecutor(self._cli_service, command_template.ADD_TO_VLAN).execute_command(
            node_name=node, vlan_id=vlan_id, port=dst_port)

        out += CommandTemplateExecutor(self._cli_service, command_template.VLE_CREATE).execute_command(
            vle_name=vle_name, node_1=node, node_1_port=src_port, node_2=node, node_2_port=dst_port)

    def delete_single_node_vle(self, node, vle_name, vlan_id):
        out = CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLE).execute_command(vle_name=vle_name)
        out += CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLAN).execute_command(node=node,
                                                                                                        vlan_id=vlan_id)

    def delete_multi_node_vle(self, src_node, dst_node, vle_name, vlan_id):
        out = CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLE).execute_command(vle_name=vle_name)
        out += CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLAN).execute_command(node=src_node,
                                                                                                        vlan_id=vlan_id)
        out += CommandTemplateExecutor(self._cli_service, command_template.DELETE_VLAN).execute_command(node=dst_node,
                                                                                                        vlan_id=vlan_id)

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

    def vlan_id_for_port(self, node, port):
        out = CommandTemplateExecutor(self._cli_service, command_template.PORT_VLAN_INFO,
                                      remove_prompt=True).execute_command(node=node, port=port)
        node_key = 'node'
        port_key = 'port'
        vlan_id_key = 'vlan'

        out_table = ActionsHelper.parse_table_by_keys(out, node_key, port_key, vlan_id_key)
        vlan_id = int(out_table[0].get(vlan_id_key))
        if vlan_id:
            return vlan_id
        raise Exception(self.__class__.__name__, 'Cannet determine vlan_id')
