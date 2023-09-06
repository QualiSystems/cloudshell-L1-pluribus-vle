from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cloudshell.cli.command_template.command_template_executor import (
    CommandTemplateExecutor,
)

import pluribus_vle.command_templates.autoload as command_template
from pluribus_vle.command_actions.actions_helper import ActionsHelper

if TYPE_CHECKING:
    from cloudshell.cli.service.cli_service import CliService


class AutoloadActions:
    """Autoload actions."""

    def __init__(self, cli_service: CliService) -> None:
        self._cli_service = cli_service

    def ports_table(self, switch_name: str) -> dict[str, dict[str, str]]:
        """Build port table."""
        port_table = {}
        logic_ports_output = CommandTemplateExecutor(
            self._cli_service, command_template.PORT_SHOW
        ).execute_command(switch_name=switch_name)

        for rec in re.findall(r"^\d+:.+:.+$", logic_ports_output, re.MULTILINE):
            port_id, speed, autoneg = re.split(r":", rec.strip())
            port_table[port_id] = {"speed": speed, "autoneg": autoneg}

        return port_table

    def associations_table(self) -> dict[tuple[str, str], tuple[str, str]]:
        """Build port mapping table."""
        output = CommandTemplateExecutor(
            self._cli_service, command_template.VLE_SHOW, remove_prompt=True
        ).execute_command()

        associations_table = {}
        for line in output.splitlines():
            match = re.match(r"\s*(.+):(.+):(.+):(.+):(.+)\s*", line)
            if match:
                master_port = (match.group(2), match.group(4))
                slave_port = (match.group(3), match.group(5))
                associations_table[master_port] = slave_port
                associations_table[slave_port] = master_port
        return associations_table

    def fabric_nodes_table(self, fabric_name: str) -> dict[str, dict[str, str]]:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.FABRIC_NODES_SHOW, remove_prompt=True
        ).execute_command(fabric_name=fabric_name)

        nodes_table = {}
        for line in out.splitlines():
            match = re.match(r".+:(.+):.+", line)
            if match:
                node_name = match.group(1).strip()
                nodes_table[node_name] = self._switch_info_table(node_name)
        return nodes_table

    def _switch_info_table(self, switch_name: str) -> dict[str, str]:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.SWITCH_INFO, remove_prompt=True
        ).execute_command(switch_name=switch_name)
        return ActionsHelper.parse_table(out)
