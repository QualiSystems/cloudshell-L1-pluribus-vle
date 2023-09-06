from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cloudshell.cli.command_template.command_template_executor import (
    CommandTemplateExecutor,
)

import pluribus_vle.command_templates.system as command_template
from pluribus_vle.command_actions.actions_helper import ActionsHelper

if TYPE_CHECKING:
    from cloudshell.cli.service.cli_service import CliService


class SystemActions:
    """System actions."""

    def __init__(self, cli_service: CliService) -> None:
        self._cli_service = cli_service
        self.__phys_to_logical_table: dict[str, str] | None = None

    @property
    def cli_service(self) -> CliService:
        return self._cli_service

    @cli_service.setter
    def cli_service(self, cli_service: CliService):
        self._cli_service = cli_service

    def _build_phys_to_logical_table(self) -> dict[str, str]:
        logical_to_phys_dict = {}
        output = CommandTemplateExecutor(
            self._cli_service, command_template.PHYS_TO_LOGICAL
        ).execute_command()
        for phys_id, logical_id in re.findall(
            r"^([\d\.]+):(\d+)$", output, flags=re.MULTILINE
        ):
            logical_to_phys_dict[phys_id] = logical_id
        return logical_to_phys_dict

    @property
    def _phys_to_logical_table(self) -> dict[str, str]:
        if not self.__phys_to_logical_table:
            self.__phys_to_logical_table = self._build_phys_to_logical_table()
        return self.__phys_to_logical_table

    def _get_logical(self, phys_name: str) -> str:
        logical_id = self._phys_to_logical_table.get(phys_name)
        if logical_id:
            return logical_id
        else:
            raise Exception("Cannot convert physical port name to logical")

    def get_state_id(self) -> str:
        state_id = CommandTemplateExecutor(
            self._cli_service, command_template.GET_STATE_ID
        ).execute_command()
        return re.split(r"\s", state_id.strip())[1]

    def set_state_id(self, state_id: str) -> str:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.SET_STATE_ID
        ).execute_command(state_id=state_id)
        return out

    def set_auto_negotiation(self, phys_port: str, node_name: str, value: str) -> None:
        logical_port_id = self._get_logical(phys_port)
        if value.lower() == "true":
            CommandTemplateExecutor(
                self._cli_service, command_template.SET_AUTO_NEG_ON
            ).execute_command(node_name=node_name, port_id=logical_port_id)
        else:
            CommandTemplateExecutor(
                self._cli_service, command_template.SET_AUTO_NEG_OFF
            ).execute_command(node_name=node_name, port_id=logical_port_id)

    def set_port_state(self, port: str, node_name: str, port_state: str) -> None:
        port_state = port_state.lower()
        if port_state not in ["enable", "disable"]:
            port_state = "enable"

        CommandTemplateExecutor(
            self._cli_service, command_template.SET_PORT_STATE
        ).execute_command(port_id=port, node_name=node_name, port_state=port_state)

    def get_fabric_info(self) -> dict[str, str]:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.FABRIC_INFO, remove_prompt=True
        ).execute_command()
        return ActionsHelper.parse_table(out)

    def tunnels_table(self) -> dict[tuple[str, str], str]:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.TUNNEL_INFO, remove_prompt=True
        ).execute_command()

        switch_key = "switch"
        tunnel_name_key = "tunnel_name"
        local_ip_key = "local_ip"
        remote_ip_key = "remote_ip"

        out_list = ActionsHelper.parse_table_by_keys(
            out, switch_key, tunnel_name_key, local_ip_key, remote_ip_key
        )
        switch_ip_table = {
            data.get(local_ip_key): data.get(switch_key) for data in out_list
        }

        tunnels_table = {}
        for data_table in out_list:
            local_switch_name = data_table.get(switch_key)
            remote_switch_name = switch_ip_table.get(data_table.get(remote_ip_key))
            tunnel_name = data_table.get(tunnel_name_key)
            if local_switch_name and remote_switch_name and tunnel_name:
                tunnels_table[local_switch_name, remote_switch_name] = tunnel_name
        return tunnels_table

    def get_available_vlan_id(self, min_vlan: int, max_vlan: int) -> int:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.VLAN_SHOW, remove_prompt=True
        ).execute_command()

        switch_name_key = "switch_name"
        vlan_id_key = "vlan_id"
        vxlan_key = "vxlan"
        description_key = "description"
        out_list = ActionsHelper.parse_table_by_keys(
            out, switch_name_key, vlan_id_key, vxlan_key, description_key
        )

        busy_vlans = [int(data[vlan_id_key]) for data in out_list]
        avail_vlan_id = list(set(range(min_vlan, max_vlan + 1)) - set(busy_vlans))[0]
        if avail_vlan_id:
            return avail_vlan_id
        raise Exception("Cannot determine available vlan id")

    def get_switch_mapping(self) -> dict[str, str]:
        """Get switch name to switch hostid mapping."""
        return {}
