from __future__ import annotations

from typing import TYPE_CHECKING

from cloudshell.cli.command_template.command_template_executor import (
    CommandTemplateExecutor,
)
from cloudshell.cli.session.session_exceptions import CommandExecutionException

import pluribus_vle.command_templates.mapping as command_template
from pluribus_vle.command_actions.actions_helper import ActionsHelper
from pluribus_vle.constants import FORBIDDEN_PORT_STATUS_TABLE

if TYPE_CHECKING:
    from cloudshell.cli.service.cli_service import CliService


class MappingActions:
    """Autoload actions."""

    def __init__(self, cli_service: CliService) -> None:
        self._cli_service = cli_service
        self.__associations_table = None
        self.__phys_to_logical_table = None

    @property
    def cli_service(self) -> CliService:
        return self._cli_service

    @cli_service.setter
    def cli_service(self, cli_service: CliService):
        self._cli_service = cli_service

    def map_bidi_multi_node(
        self,
        src_node: str,
        dst_node: str,
        src_port: str,
        dst_port: str,
        src_tunnel: str,
        dst_tunnel: str,
        vlan_id: int,
        vle_name: str,
    ) -> None:
        """Create bidi connection for ports on different nodes."""
        self._validate_port(src_node, src_port)
        self._validate_port(dst_node, dst_port)
        self._create_vlan(src_node, src_port, vlan_id)
        out = CommandTemplateExecutor(
            self._cli_service, command_template.ADD_VXLAN_TO_TUNNEL
        ).execute_command(node_name=src_node, tunnel_name=src_tunnel, vxlan_id=vlan_id)
        self._validate_vxlan_add(src_node, vlan_id, src_tunnel)

        self._create_vlan(dst_node, dst_port, vlan_id)
        out += CommandTemplateExecutor(
            self._cli_service, command_template.ADD_VXLAN_TO_TUNNEL
        ).execute_command(node_name=dst_node, tunnel_name=dst_tunnel, vxlan_id=vlan_id)
        self._validate_vxlan_add(dst_node, vlan_id, dst_tunnel)

        out += CommandTemplateExecutor(
            self._cli_service, command_template.VLE_CREATE
        ).execute_command(
            vle_name=vle_name,
            node_1=src_node,
            node_1_port=src_port,
            node_2=dst_node,
            node_2_port=dst_port,
        )
        self._validate_vle_creation(vle_name)

    def map_bidi_single_node(
        self, node: str, src_port: str, dst_port: str, vlan_id: int, vle_name: str
    ) -> None:
        """Create bidi connection for ports on same node."""
        self._validate_port(node, src_port)
        self._validate_port(node, dst_port)
        self._create_vlan(node, src_port, vlan_id)
        self._add_to_vlan(node, dst_port, vlan_id)

        CommandTemplateExecutor(
            self._cli_service, command_template.VLE_CREATE
        ).execute_command(
            vle_name=vle_name,
            node_1=node,
            node_1_port=src_port,
            node_2=node,
            node_2_port=dst_port,
        )
        self._validate_vle_creation(vle_name)

    def delete_single_node_vle(self, node: str, vle_name: str, vlan_id: int) -> None:
        """Remove VLE on single node."""
        out = CommandTemplateExecutor(
            self._cli_service, command_template.DELETE_VLE
        ).execute_command(vle_name=vle_name)
        self._validate_vle_deletion(vle_name)
        out += CommandTemplateExecutor(
            self._cli_service, command_template.DELETE_VLAN
        ).execute_command(node=node, vlan_id=vlan_id)
        self._validate_vlan_id_deletion(node, vlan_id)

    def delete_multi_node_vle(
        self, src_node: str, dst_node: str, vle_name: str, vlan_id: int
    ) -> None:
        """Remove VLE between different nodes."""
        out = CommandTemplateExecutor(
            self._cli_service, command_template.DELETE_VLE
        ).execute_command(vle_name=vle_name)
        self._validate_vle_deletion(vle_name)
        out += CommandTemplateExecutor(
            self._cli_service, command_template.DELETE_VLAN
        ).execute_command(node=src_node, vlan_id=vlan_id)
        self._validate_vlan_id_deletion(src_node, vlan_id)
        out += CommandTemplateExecutor(
            self._cli_service, command_template.DELETE_VLAN
        ).execute_command(node=dst_node, vlan_id=vlan_id)
        self._validate_vlan_id_deletion(dst_node, vlan_id)

    def connection_table(self) -> dict[tuple[str, str], tuple[tuple[str, str], str]]:
        """Build connection table."""
        connection_table = {}
        out = CommandTemplateExecutor(
            self._cli_service, command_template.VLE_SHOW, remove_prompt=True
        ).execute_command()

        vle_name_key = "vle_name"
        node_1_key = "node_1"
        node_2_key = "node_2"
        node_1_port_key = "node_1_port"
        node_2_port_key = "node_2_port"

        out_table = ActionsHelper.parse_table_by_keys(
            out, vle_name_key, node_1_key, node_2_key, node_1_port_key, node_2_port_key
        )
        for record in out_table:
            src_record = (record[node_1_key], record[node_1_port_key])
            dst_record = (record[node_2_key], record[node_2_port_key])
            vle_name = record[vle_name_key]
            connection_table[src_record] = (dst_record, vle_name)
            connection_table[dst_record] = (src_record, vle_name)
        return connection_table

    def _create_vlan(self, node: str, port: str, vlan_id: int) -> None:
        self._remove_port_from_vlans(node, port)
        self._validate_port_is_not_a_member(node, port)
        CommandTemplateExecutor(
            self._cli_service,
            command_template.CREATE_VLAN,
        ).execute_command(node_name=node, vlan_id=vlan_id, vxlan_id=vlan_id, port=port)
        self._validate_port_is_a_member(node, port, vlan_id)

    def _add_to_vlan(self, node: str, port: str, vlan_id: int) -> None:
        self._remove_port_from_vlans(node, port)
        self._validate_port_is_not_a_member(node, port)
        CommandTemplateExecutor(
            self._cli_service, command_template.ADD_TO_VLAN
        ).execute_command(node_name=node, vlan_id=vlan_id, port=port)
        self._validate_port_is_a_member(node, port, vlan_id)

    def _validate_port_is_not_a_member(self, node: str, port: str) -> None:
        vlan_members = self.vlan_ids_for_port(node, port)
        if vlan_members and len(set(vlan_members) - {1}) > 0:
            raise CommandExecutionException(
                f"Port {(node, port)} already a member of vlan_id {vlan_members}"
            )

    def _validate_port_is_a_member(self, node: str, port: str, vlan_id: int) -> None:
        vlan_members = self.vlan_ids_for_port(node, port)
        if not vlan_members or int(vlan_id) not in vlan_members:
            raise CommandExecutionException(
                f"Cannot add port {(node, port)} to vlan {vlan_id}"
            )

    def _validate_vxlan_add(self, node_name: str, vxlan_id: int, tunnel: str) -> None:
        switch_key = "switch"
        tunnel_name_key = "tunnel_name"
        vxlan_id_key = "vxlan_id"
        out = CommandTemplateExecutor(
            self._cli_service, command_template.VXLAN_SHOW, remove_prompt=True
        ).execute_command(node_name=node_name, vxlan_id=vxlan_id)
        out_table = ActionsHelper.parse_table_by_keys(
            out, switch_key, tunnel_name_key, vxlan_id_key
        )
        active_tunnels = [record[tunnel_name_key] for record in out_table]
        if tunnel in active_tunnels:
            return
        raise CommandExecutionException(
            f"Failed to add vxlan {vxlan_id} to tunnel {tunnel},"
            f"see driver logs for more details"
        )

    def _validate_vle_creation(self, vle_name: str) -> None:
        vle_name_key = "vle_name"
        node_1_key = "node_1"
        node_2_key = "node_2"
        node_1_port_key = "node_1_port"
        node_2_port_key = "node_2_port"
        status_key = "status"
        out = CommandTemplateExecutor(
            self._cli_service, command_template.VLE_SHOW_FOR_NAME, remove_prompt=True
        ).execute_command(vle_name=vle_name)
        out_table = ActionsHelper.parse_table_by_keys(
            out,
            vle_name_key,
            node_1_key,
            node_1_port_key,
            node_2_key,
            node_2_port_key,
            status_key,
        )
        if not out_table or out_table[0].get(vle_name_key) != vle_name:
            raise CommandExecutionException(
                f"VLE {vle_name} creation failed, see logs for more details"
            )

    def _validate_vle_deletion(self, vle_name: str) -> None:
        vle_name_key = "vle_name"
        node_1_key = "node_1"
        node_2_key = "node_2"
        node_1_port_key = "node_1_port"
        node_2_port_key = "node_2_port"
        status_key = "status"
        out = CommandTemplateExecutor(
            self._cli_service, command_template.VLE_SHOW_FOR_NAME, remove_prompt=True
        ).execute_command(vle_name=vle_name)
        out_table = ActionsHelper.parse_table_by_keys(
            out,
            vle_name_key,
            node_1_key,
            node_1_port_key,
            node_2_key,
            node_2_port_key,
            status_key,
        )
        if out_table:
            raise CommandExecutionException(
                f"Failed to delete VLE {vle_name}, see logs for more details"
            )

    def _validate_vlan_id_deletion(self, node_name: str, vlan_id: int) -> None:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.VLAN_SHOW, remove_prompt=True
        ).execute_command(node_name=node_name, vlan_id=vlan_id)
        vlan_id_key = "vlan_id"
        switch_key = "switch_key"
        vxlan_id_key = "vxlan"
        out_table = ActionsHelper.parse_table_by_keys(
            out, vlan_id_key, switch_key, vxlan_id_key
        )
        if out_table:
            raise CommandExecutionException(
                f"Failed to delete vlan {vlan_id} on node {node_name}"
            )

    def vlan_ids_for_port(self, node: str, port: str) -> list[int]:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.PORT_VLAN_INFO, remove_prompt=True
        ).execute_command(node=node, port=port)
        node_key = "node"
        port_key = "port"
        vlan_id_key = "vlan"

        out_table = ActionsHelper.parse_table_by_keys(
            out, node_key, port_key, vlan_id_key
        )
        value = out_table[0].get(vlan_id_key)
        if value is not None and value.lower() != "none":
            return list(map(int, value.split(",")))

        return []

    def _validate_port(self, node_name: str, port: str) -> None:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.PORT_STATUS_SHOW, remove_prompt=True
        ).execute_command(node_name=node_name, port=port)
        node_key = "node"
        port_key = "port"
        status_key = "status"

        out_table = ActionsHelper.parse_table_by_keys(
            out, node_key, port_key, status_key
        )
        if out_table:
            status_data = out_table[0].get(status_key)
            if status_data:
                for status in status_data.split(","):
                    if status.strip().lower() in FORBIDDEN_PORT_STATUS_TABLE:
                        raise CommandExecutionException(
                            f"Port {(node_name, port)} is not allowed to use for VLE,"
                            f"it has status {status}."
                        )

    def _remove_from_vlan(self, node_name: str, vlan_id: int, port: str) -> None:
        out = CommandTemplateExecutor(
            self._cli_service, command_template.REMOVE_FROM_VLAN, remove_prompt=True
        ).execute_command(node_name=node_name, vlan_id=vlan_id, port=port)
        if "removed" not in out.lower():
            raise CommandExecutionException(
                f"Cannot remove port {port} from VlanId {vlan_id} on node {node_name}"
            )

    def _remove_port_from_vlans(self, node: str, port: str) -> None:
        vlan_members = self.vlan_ids_for_port(node, port)
        if vlan_members is not None:
            for vlan_id in vlan_members:
                self._remove_from_vlan(node, vlan_id, port)
