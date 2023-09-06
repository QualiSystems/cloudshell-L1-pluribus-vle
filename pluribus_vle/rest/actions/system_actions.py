from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pluribus_vle.rest.api_handler import PluribusRESTAPI


class RestSystemActions:
    """System actions."""

    def __init__(self, api: PluribusRESTAPI) -> None:
        self._api = api
        self.__phys_to_logical_table: dict[str, str] = {}

    def _build_phys_to_logical_table(self) -> dict[str, str]:
        """Get physical to logical mapping."""
        logical_to_phys_dict = {}
        data = self._api.get_phy_to_logical()
        for portmap in data:
            logical_to_phys_dict[portmap["bezel-intf"]] = portmap["port"]

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
        data = self._api.get_switch_setup()[0]
        return data["motd"]

    def set_state_id(self, state_id) -> None:
        self._api.set_state_id(state_id=state_id)

    def set_auto_negotiation(self, phys_port: str, node_id: int, value: str) -> None:
        """Set auto-negotiation value."""
        logical_port_id = self._get_logical(phys_port)
        if value.lower() == "true":
            is_autoneg = True
        else:
            is_autoneg = False
        self._api.set_autoneg(
            port_id=logical_port_id, hostid=node_id, is_autoneg=is_autoneg
        )

    def set_port_state(self, port: str, node_id: str, port_state: str) -> None:
        """Enable/Disable port."""
        port_state = port_state.lower()
        if port_state not in ["enable", "disable"]:
            port_state = "enable"
        self._api.set_port_state(port_id=port, hostid=node_id, port_state=port_state)

    def get_fabric_info(self) -> dict[str, str]:
        """Get fabric information."""
        data = self._api.get_fabric_info()
        return data[0]

    def tunnels_table(self) -> dict[tuple[str, str], str]:
        """Get tunnels information."""
        switch_key = "api.switch-name"
        tunnel_name_key = "name"
        local_ip_key = "local-ip"
        remote_ip_key = "remote-ip"

        data = self._api.get_tunnel_info()

        switch_ip_table = {
            tunnel.get(local_ip_key): tunnel.get(switch_key) for tunnel in data
        }
        tunnels_table = {}
        for tunnel in data:
            local_switch_name = tunnel.get(switch_key)
            remote_switch_name = switch_ip_table.get(tunnel.get(remote_ip_key))
            tunnel_name = tunnel.get(tunnel_name_key)
            if local_switch_name and remote_switch_name and tunnel_name:
                tunnels_table[local_switch_name, remote_switch_name] = tunnel_name
        return tunnels_table

    def get_available_vlan_id(self, min_vlan: int, max_vlan: int) -> int:
        """Get available VLAN."""
        data = self._api.get_vlans()
        busy_vlans = [int(vlan["id"]) for vlan in data]
        available_vlan_ids = list(set(range(min_vlan, max_vlan + 1)) - set(busy_vlans))
        if available_vlan_ids:
            return available_vlan_ids[0]
        raise Exception("Cannot determine available vlan id")

    def get_switch_mapping(self) -> dict[str, str]:
        """Get switch name to switch hostid mapping."""
        data = self._api.get_switch_setup(fabric=True)
        return {switch["switch-name"]: switch["hostid"] for switch in data}
