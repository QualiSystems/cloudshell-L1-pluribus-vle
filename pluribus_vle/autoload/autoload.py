from __future__ import annotations

from pluribus_vle.autoload.vle_blade import VLEBlade
from pluribus_vle.autoload.vle_fabric import VLEFabric
from pluribus_vle.autoload.vle_port import VLEPort


class Autoload:
    def __init__(
        self,
        resource_address: str,
        fabric_name: str,
        fabric_id: str,
        nodes_table: dict[str, dict[str, str]],
        ports_table: dict[str, dict[str, dict[str, str]]],
        associations_table: dict[tuple[str, str], tuple[str, str]],
    ) -> None:
        self._fabric_name = fabric_name
        self._fabric_id = fabric_id
        self._nodes_table = nodes_table
        self._ports_table = ports_table
        self._resource_address = resource_address
        self._associations_table = associations_table

    def _build_fabric(self) -> VLEFabric:
        """Get base fabric info."""
        fabric = VLEFabric(self._fabric_name, self._resource_address, self._fabric_id)
        fabric.set_fabric_name(self._fabric_name)
        fabric.set_serial_number(self._fabric_id)
        return fabric

    def build_fabric_nodes(self, fabric: VLEFabric) -> dict[str, VLEBlade]:
        """Build nodes for provided fabric."""
        nodes_dict = {}
        for node_name, node_data in self._nodes_table.items():
            node = VLEBlade(node_name)
            node.set_model_name(node_data.get("model"))
            node.set_serial_number(node_data.get("chassis-serial"))
            node.set_parent_resource(fabric)
            nodes_dict[node_name] = node
        return nodes_dict

    def _build_ports(
        self, nodes_dict: dict[str, VLEBlade]
    ) -> dict[tuple[str, str], VLEPort]:
        """Build ports for all nodes."""
        ports_dict = {}
        for node_id, ports_data in self._ports_table.items():
            fabric_node = nodes_dict[node_id]
            ports_dict.update(self._build_ports_for_node(fabric_node, ports_data))
        return ports_dict

    def _build_ports_for_node(
        self, fabric_node: VLEBlade, ports_data: dict[str, dict[str, str]]
    ) -> dict[tuple[str, str], VLEPort]:
        """Build ports info for provided node."""
        ports_dict = {}

        for port_id, port_record in ports_data.items():
            speed = port_record.get("speed")
            autoneg = port_record.get("autoneg")

            port = VLEPort(port_id)
            port.set_model_name(f"{fabric_node.get_model_name()} Port")
            port.set_auto_negotiation(autoneg == "on")
            port.set_port_speed(speed)
            port.set_parent_resource(fabric_node)
            ports_dict[(fabric_node.resource_id, port_id)] = port
        return ports_dict

    def _build_mappings(self, ports_dict):
        """Build port mappings."""
        for slave_port_id, master_port_id in self._associations_table.items():
            slave_port = ports_dict.get(slave_port_id)
            master_port = ports_dict.get(master_port_id)
            if slave_port and master_port:
                slave_port.add_mapping(master_port)

    def build_structure(self):
        """Build device structure."""
        fabric = self._build_fabric()
        nodes_dict = self.build_fabric_nodes(fabric)
        ports_dict = self._build_ports(nodes_dict)
        self._build_mappings(ports_dict)
        return [fabric]
