#!/usr/bin/python
# -*- coding: utf-8 -*-
import re

import pluribus_vle.command_templates.autoload as command_template

from cloudshell.cli.command_template.command_template_executor import \
    CommandTemplateExecutor
from pluribus_vle.command_actions.actions_helper import ActionsHelper


class AutoloadActions(object):
    """ Autoload actions. """

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

    def ports_table(self, switch_name):
        """ """
        port_table = {}
        logic_ports_output = CommandTemplateExecutor(
            self._cli_service,
            command_template.PORT_SHOW
        ).execute_command(switch_name=switch_name)

        for record in re.findall(r"^\d+:.+:.+$", logic_ports_output,
                                 flags=re.MULTILINE):
            port_id, speed, autoneg = re.split(r":", record.strip())
            port_id = port_id
            speed = speed
            autoneg = autoneg
            port_table[port_id] = {"speed": speed, "autoneg": autoneg}

        return port_table

    def associations_table(self):
        out = CommandTemplateExecutor(self._cli_service, command_template.VLE_SHOW,
                                      remove_prompt=True).execute_command()

        associations_table = {}
        for line in out.splitlines():
            match = re.match(r"\s*(.+)\:(.+)\:(.+)\:(.+)\:(.+)\s*", line)
            if match:
                master_port = (match.group(2), match.group(4))
                slave_port = (match.group(3), match.group(5))
                associations_table[master_port] = slave_port
                associations_table[slave_port] = master_port
        return associations_table

    def fabric_nodes_table(self, fabric_name):

        out = CommandTemplateExecutor(self._cli_service,
                                      command_template.FABRIC_NODES_SHOW,
                                      remove_prompt=True).execute_command(
            fabric_name=fabric_name)
        nodes_table = {}
        for line in out.splitlines():
            match = re.match(r".+\:(.+)\:.+", line)
            if match:
                node_name = match.group(1).strip()
                nodes_table[node_name] = self._switch_info_table(node_name)
        return nodes_table

    def _switch_info_table(self, switch_name):
        out = CommandTemplateExecutor(self._cli_service, command_template.SWITCH_INFO,
                                      remove_prompt=True).execute_command(
            switch_name=switch_name)
        return ActionsHelper.parse_table(out)
