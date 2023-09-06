from __future__ import annotations

from cloudshell.cli.command_template.command_template import CommandTemplate

ERROR_MAP: dict = {r"[Ee]rror:": "Command error"}

GET_STATE_ID = CommandTemplate("switch-setup-show format motd", error_map=ERROR_MAP)
SET_STATE_ID = CommandTemplate(
    "switch-setup-modify motd {state_id}", error_map=ERROR_MAP
)
SET_AUTO_NEG_ON = CommandTemplate(
    "switch {node_name} port-config-modify port {port_id} autoneg", error_map=ERROR_MAP
)
SET_AUTO_NEG_OFF = CommandTemplate(
    "switch {node_name} port-config-modify port {port_id} no-autoneg",
    error_map=ERROR_MAP,
)
SET_PORT_STATE = CommandTemplate(
    "switch {node_name} port-config-modify port {port_id} {port_state}",
    error_map=ERROR_MAP,
)
PHYS_TO_LOGICAL = CommandTemplate(
    'bezel-portmap-show format bezel-intf,port parsable-delim ":"', error_map=ERROR_MAP
)
FABRIC_INFO = CommandTemplate('fabric-info parsable-delim ":"', error_map=ERROR_MAP)
TUNNEL_INFO = CommandTemplate(
    "tunnel-show auto-tunnel static format switch,name,local-ip,remote-ip, "
    'parsable-delim ":"',
    error_map=ERROR_MAP,
)
VLAN_SHOW = CommandTemplate(
    'vlan-show format switch,id,vxlan,description, parsable-delim ":"',
    error_map=ERROR_MAP,
)
