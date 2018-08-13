import re

import pluribus_netvisor_vle.command_templates.system as command_template
from cloudshell.cli.command_template.command_template_executor import CommandTemplateExecutor
from pluribus_netvisor_vle.command_actions.actions_helper import ActionsHelper


class SystemActions(object):
    """
    Autoload actions
    """

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

    def get_fabric_name(self):
        out = CommandTemplateExecutor(self._cli_service, command_template.FABRIC_INFO,
                                      remove_prompt=True).execute_command()
        return ActionsHelper.parse_table(out).get('name')
