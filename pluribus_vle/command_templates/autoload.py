from __future__ import annotations

from cloudshell.cli.command_template.command_template import CommandTemplate

ERROR_MAP: dict = {r"[Ee]rror:": "Command error"}

SWITCH_INFO = CommandTemplate(
    'switch "{switch_name}" switch-info-show '
    'format model,chassis-serial parsable-delim ":"',
    error_map=ERROR_MAP,
)
SWITCH_SETUP = CommandTemplate(
    "switch-setup-show format switch-name", error_map=ERROR_MAP
)
SOFTWARE_VERSION = CommandTemplate("software-show", error_map=ERROR_MAP)
PORT_SHOW = CommandTemplate(
    'switch "{switch_name}" port-config-show format port,speed,autoneg '
    'parsable-delim ":"',
    error_map=ERROR_MAP,
)
PHYS_PORT_SHOW = CommandTemplate(
    'switch "{switch_name}" bezel-portmap-show format port,bezel-intf '
    'parsable-delim ":"',
    error_map=ERROR_MAP,
)
ASSOCIATIONS = CommandTemplate(
    "port-association-show format master-ports,slave-ports,bidir " 'parsable-delim ":"',
    error_map=ERROR_MAP,
)
FABRIC_NODES_SHOW = CommandTemplate(
    'fabric-node-show fab-name "{fabric_name}" format fab-name,name,in-band-ip '
    'parsable-delim ":"',
    error_map=ERROR_MAP,
)
VLE_SHOW = CommandTemplate(
    'vle-show format name,node-1,node-2,node-1-port,node-2-port parsable-delim ":"',
    error_map=ERROR_MAP,
)
