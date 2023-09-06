from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pluribus_vle.rest.api_handler import PluribusRESTAPI

from pluribus_vle.constants import FORBIDDEN_PORT_STATUS_TABLE
from pluribus_vle.rest.api_handler import PluribusApiException


class RestMappingActions:
    """Mapping actions."""

    def __init__(self, api: PluribusRESTAPI, switch_mapping: dict[str, str]) -> None:
        self._api = api
        self._switch_mapping = switch_mapping
        self.__associations_table = None
        self.__phys_to_logical_table = None

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
        """Create BiDirectional connection on multiple nodes."""
        src_node_id = self._switch_mapping.get(src_node, "fabric")
        dst_node_id = self._switch_mapping.get(dst_node, "fabric")
        self._validate_port(src_node, src_port)
        self._validate_port(dst_node, dst_port)

        self._create_vlan(src_node, src_port, vlan_id)
        self._api.add_vxlan_to_tunnel(
            tunnel_name=src_tunnel, vxlan_id=vlan_id, hostid=src_node_id
        )
        self._validate_vxlan_add(src_node, vlan_id, src_tunnel)

        self._create_vlan(dst_node, dst_port, vlan_id)
        self._api.add_vxlan_to_tunnel(
            tunnel_name=dst_tunnel, vxlan_id=vlan_id, hostid=dst_node_id
        )
        self._validate_vxlan_add(dst_node, vlan_id, dst_tunnel)

        self._api.create_vles(
            vle_name=vle_name,
            node_1=src_node_id,
            node_1_port=src_port,
            node_2=dst_node_id,
            node_2_port=dst_port,
        )
        if not self._validate_is_vle_exists(vle_name):
            raise PluribusApiException(
                f"VLE {vle_name} creation failed, see logs for more details"
            )

    def map_bidi_single_node(
        self, node: str, src_port: str, dst_port: str, vlan_id: int, vle_name: str
    ) -> None:
        """Create BiDirectional connection on single node."""
        node_id = self._switch_mapping.get(node, "fabric")
        self._validate_port(node, src_port)
        self._validate_port(node, dst_port)
        self._create_vlan(node, src_port, vlan_id)
        self._add_to_vlan(node, dst_port, vlan_id)

        self._api.create_vles(
            vle_name=vle_name,
            node_1=node_id,
            node_1_port=src_port,
            node_2=node_id,
            node_2_port=dst_port,
        )

        if not self._validate_is_vle_exists(vle_name):
            raise PluribusApiException(
                f"VLE {vle_name} creation failed, see logs for more details"
            )

    def delete_single_node_vle(self, node: str, vle_name: str, vlan_id: int) -> None:
        """Delete VLE on single node."""
        if self._validate_is_vle_exists(vle_name):
            self._api.delete_vles(vle_name=vle_name)
            if self._validate_is_vle_exists(vle_name):
                raise PluribusApiException(
                    f"Failed to delete VLE {vle_name}, see logs for more details"
                )

            self._api.delete_vlan(
                vlan_id=vlan_id, hostid=self._switch_mapping.get(node, "fabric")
            )

            if self._validate_vlan_exists(node, vlan_id):
                raise PluribusApiException(
                    f"Failed to delete vlan {vlan_id} on node {node}"
                )

    def delete_multi_node_vle(
        self, src_node: str, dst_node: str, vle_name: str, vlan_id: int
    ) -> None:
        """Delete VLE on multiple nodes."""
        if self._validate_is_vle_exists(vle_name):
            self._api.delete_vles(vle_name=vle_name)
            if self._validate_is_vle_exists(vle_name):
                raise PluribusApiException(
                    f"Failed to delete VLE {vle_name}, see logs for more details"
                )

            for node_name in [src_node, dst_node]:
                if self._validate_vlan_exists(node_name, vlan_id):
                    self._api.delete_vlan(
                        vlan_id=vlan_id,
                        hostid=self._switch_mapping.get(node_name, "fabric"),
                    )
                    if self._validate_vlan_exists(node_name, vlan_id):
                        raise PluribusApiException(
                            "Failed to delete vlan {vlan_id} on node {node_name}"
                        )

    def connection_table(self) -> dict[tuple[str, str], tuple[tuple[str, str], str]]:
        """Build connection table."""
        connection_table = {}
        data = self._api.get_vles()
        for vle in data:
            src_record = (vle["node1-name"], str(vle["node-1-port"]))
            dst_record = (vle["node2-name"], str(vle["node-2-port"]))
            connection_table.update(
                {
                    src_record: (dst_record, vle["name"]),
                    dst_record: (src_record, vle["name"]),
                }
            )
        return connection_table

    def _create_vlan(self, node: str, port: str, vlan_id: int) -> None:
        """Create VLAN."""
        self._remove_port_from_vlans(node, port)
        self._validate_port_is_not_a_member(node, port)

        self._api.create_vlan(
            vlan_id=vlan_id,
            vxlan_id=vlan_id,
            port=port,
            hostid=self._switch_mapping.get(node, "fabric"),
        )
        self._validate_port_is_a_member(node, port, vlan_id)

    def _add_to_vlan(self, node: str, port: str, vlan_id: int) -> None:
        """Add port to VLAN."""
        self._remove_port_from_vlans(node, port)
        self._validate_port_is_not_a_member(node, port)

        self._api.add_ports_to_vlan(
            vlan_id=vlan_id, port=port, hostid=self._switch_mapping.get(node, "fabric")
        )
        self._validate_port_is_a_member(node, port, vlan_id)

    def _validate_port_is_not_a_member(self, node: str, port: str) -> None:
        vlan_members = self.vlan_ids_for_port(node, port)
        if vlan_members and len(set(vlan_members) - {1}) > 0:
            raise PluribusApiException(
                f"Port {(node, port)} already a member of vlan_id {vlan_members}"
            )

    def _validate_port_is_a_member(self, node: str, port: str, vlan_id: int) -> None:
        vlan_members = self.vlan_ids_for_port(node, port)
        if not vlan_members or int(vlan_id) not in vlan_members:
            raise PluribusApiException(
                f"Cannot add port {(node, port)} to vlan {vlan_id}"
            )

    def _validate_vxlan_add(self, node_name: str, vxlan_id: int, tunnel: str) -> None:
        """Validate VXLAN is exists."""
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.get_tunnel_vxlans(tunnel=tunnel, hostid=node_id)

        for vxlan in data:
            if vxlan.get("vxlan", -1) == vxlan_id:
                return

        raise PluribusApiException(
            f"Failed to add vxlan {vxlan_id} to tunnel {tunnel},"
            f"see driver logs for more details"
        )

    def _validate_is_vle_exists(self, vle_name: str) -> bool:
        """Validate is VLE exists."""
        data = self._api.get_vles()

        if data:
            for vle in data:
                if vle.get("name") == vle_name:
                    return True

        return False

    def _validate_vlan_exists(self, node_name: str, vlan_id: int) -> bool:
        """Validate is VLAN deleted successfully."""
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.get_vlans(hostid=node_id)
        if data:
            for vlan in data:
                if vlan.get("id") == vlan_id:
                    return True
        return False

    def vlan_ids_for_port(self, node: str, port: str) -> list[int]:
        """Get all VLANs for port."""
        node_id = self._switch_mapping.get(node, "fabric")
        data = self._api.get_port_vlan_info(port=port, hostid=node_id)

        if data and data[0].get("vlans", ""):
            return list(map(int, data[0].get("vlans", "").split(",")))

        return []

    def _validate_port(self, node_name: str, port: str) -> None:
        """Validate port."""
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.get_port_status(port=port, hostid=node_id)

        if data:
            status_data = data[0].get("status")
            if status_data:
                for status in status_data.split(","):
                    if status.strip().lower() in FORBIDDEN_PORT_STATUS_TABLE:
                        raise PluribusApiException(
                            f"Port {(node_name, port)} is not allowed to use for VLE,"
                            f"it has status {status}"
                        )

    def _remove_from_vlan(self, node_name: str, vlan_id: int, port: str) -> None:
        """Remove port from VLAN."""
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.delete_ports_from_vlan(
            vlan_id=vlan_id, ports=port, hostid=node_id
        )

        if "removed" not in data.lower():
            raise PluribusApiException(
                f"Cannot remove port {port} from VlanId {vlan_id} on node {node_name}"
            )

    def _remove_port_from_vlans(self, node: str, port: str) -> None:
        """Remove port from VLANs."""
        vlan_members = self.vlan_ids_for_port(node, port)
        if vlan_members is not None:
            for vlan_id in vlan_members:
                self._remove_from_vlan(node, vlan_id, port)
