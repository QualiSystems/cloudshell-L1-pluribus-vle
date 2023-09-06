from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pluribus_vle.rest.api_handler import PluribusRESTAPI


class RestAutoloadActions:
    """Autoload actions."""

    def __init__(self, api: PluribusRESTAPI, switch_mapping: dict[str, str]) -> None:
        self._api = api
        self._switch_mapping = switch_mapping

    def ports_table(self, switch_name: str) -> dict[str, dict[str, str]]:
        """Get ports table."""
        port_table = {}
        data = self._api.get_port_config(
            hostid=self._switch_mapping.get(switch_name, "fabric")
        )

        for port in data:
            port_table[port["port"]] = {
                "speed": str(port.get("speed", "")),
                "autoneg": port.get("autoneg"),
            }

        return port_table

    def associations_table(self) -> dict[tuple[str, str], tuple[str, str]]:
        """Get node-port associations table."""
        associations_table = {}

        data = self._api.get_vles()
        for vle in data:
            master_port = (vle["node1-name"], str(vle["node-1-port"]))
            slave_port = (vle["node2-name"], str(vle["node-2-port"]))
            associations_table.update(
                {master_port: slave_port, slave_port: master_port}
            )
        return associations_table

    def fabric_nodes_table(self, fabric_name: str) -> dict[str, dict[str, str]]:
        """Get fabric nodes data."""
        nodes_table = {}

        data = self._api.get_fabric_nodes(fabric_name=fabric_name)
        for node in data:
            nodes_table[node["name"]] = self._switch_info_table(node["id"])

        return nodes_table

    def _switch_info_table(self, switch_id: str) -> dict[str, str]:
        """Get switch info."""
        data = self._api.get_switch_info(hostid=switch_id)[0]

        return {
            "model": data.get("model", "Undefined"),
            "chassis-serial": data.get("chassis-serial", "Undefined"),
        }
