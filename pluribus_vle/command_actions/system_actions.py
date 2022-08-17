import re

import pluribus_vle.command_templates.system as command_template
from cloudshell.cli.command_template.command_template_executor import CommandTemplateExecutor
from pluribus_vle.command_actions.actions_helper import ActionsHelper


class SystemActions(object):
    """ System actions """

    def __init__(self, cli_service, logger):
        """
        :param cli_service: default mode cli_service
        :type cli_service: CliService
        :param logger:
        :type logger: Logger
        :return:
        """
        self._cli_service = cli_service
        self._logger = logger

        self.__phys_to_logical_table = None

    @property
    def cli_service(self):
        return self._cli_service

    @cli_service.setter
    def cli_service(self, cli_service):
        self._cli_service = cli_service

    def _build_phys_to_logical_table(self):
        logical_to_phys_dict = {}
        output = CommandTemplateExecutor(self._cli_service, command_template.PHYS_TO_LOGICAL).execute_command()
        for phys_id, logical_id in re.findall(r'^([\d\.]+):(\d+)$', output, flags=re.MULTILINE):
            logical_to_phys_dict[phys_id] = logical_id
        return logical_to_phys_dict

    @property
    def _phys_to_logical_table(self):
        if not self.__phys_to_logical_table:
            self.__phys_to_logical_table = self._build_phys_to_logical_table()
        return self.__phys_to_logical_table

    def _get_logical(self, phys_name):
        logical_id = self._phys_to_logical_table.get(phys_name)
        if logical_id:
            return logical_id
        else:
            raise Exception(self.__class__.__name__, 'Cannot convert physical port name to logical')

    def get_state_id(self):
        state_id = CommandTemplateExecutor(self._cli_service, command_template.GET_STATE_ID).execute_command()
        return re.split(r'\s', state_id.strip())[1]

    def set_state_id(self, state_id):
        out = CommandTemplateExecutor(self._cli_service, command_template.SET_STATE_ID).execute_command(
            state_id=state_id)
        return out

    def set_auto_negotiation(self, phys_port, value):
        logical_port_id = self._get_logical(phys_port)
        if value.lower() == 'true':
            out = CommandTemplateExecutor(self._cli_service, command_template.SET_AUTO_NEG_ON).execute_command(
                port_id=logical_port_id)
        else:
            out = CommandTemplateExecutor(self._cli_service, command_template.SET_AUTO_NEG_OFF).execute_command(
                port_id=logical_port_id)

    def set_port_state(self, port, port_state):
        port_state = port_state.lower()
        if port_state not in ["enable", "disable"]:
            port_state = "enable"

        CommandTemplateExecutor(
            self._cli_service,
            command_template.SET_PORT_STATE
            ).execute_command(port_id=port,
                              port_state=port_state)

    def get_fabric_info(self):
        out = CommandTemplateExecutor(self._cli_service, command_template.FABRIC_INFO,
                                      remove_prompt=True).execute_command()
        return ActionsHelper.parse_table(out)

    def tunnels_table(self):
        out = CommandTemplateExecutor(self._cli_service, command_template.TUNNEL_INFO,
                                      remove_prompt=True).execute_command()
        switch_key = 'switch'
        tunnel_name_key = 'tunnel_name'
        local_ip_key = 'local_ip'
        remote_ip_key = 'remote_ip'
        # out_list = []
        # for line in out.splitlines():
        #     values = line.strip().split(':')
        #     if len(values) == 4:
        #         result = {switch_key: values[0], tunnel_name_key: values[1], local_ip_key: values[2],
        #                   remote_ip_key: values[3]}
        #         out_list.append(result)
        out_list = ActionsHelper.parse_table_by_keys(out, switch_key, tunnel_name_key, local_ip_key, remote_ip_key)
        switch_ip_table = {data.get(local_ip_key): data.get(switch_key) for data in out_list}
        tunnels_table = {}
        for data_table in out_list:
            local_switch_name = data_table.get(switch_key)
            remote_switch_name = switch_ip_table.get(data_table.get(remote_ip_key))
            tunnel_name = data_table.get(tunnel_name_key)
            if local_switch_name and remote_switch_name and tunnel_name:
                tunnels_table[local_switch_name, remote_switch_name] = tunnel_name
        return tunnels_table

    def get_available_vlan_id(self, min_vlan, max_vlan):
        out = CommandTemplateExecutor(self._cli_service, command_template.VLAN_SHOW,
                                      remove_prompt=True).execute_command()
        switch_name_key = 'switch_name'
        vlan_id_key = 'vlan_id'
        vxlan_key = 'vxlan'
        description_key = 'description'
        out_list = ActionsHelper.parse_table_by_keys(out, switch_name_key, vlan_id_key, vxlan_key, description_key)
        busy_vlans = [int(data[vlan_id_key]) for data in out_list]
        available_vlan_id = list(set(range(min_vlan, max_vlan + 1)) - set(busy_vlans))[0]
        if available_vlan_id:
            return available_vlan_id
        raise Exception(self.__class__.__name__, 'Cannot determine available vlan id')
