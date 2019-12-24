from collections import OrderedDict

from cloudshell.cli.command_template.command_template import CommandTemplate

ACTION_MAP = OrderedDict()
ERROR_MAP = OrderedDict([(r'[Ee]rror:', 'Command error')])

GET_STATE_ID = CommandTemplate('switch-setup-show format motd', ACTION_MAP, ERROR_MAP)
SET_STATE_ID = CommandTemplate('switch-setup-modify motd {state_id}', ACTION_MAP, ERROR_MAP)
SET_AUTO_NEG_ON = CommandTemplate('port-config-modify port {port_id} autoneg', ACTION_MAP, ERROR_MAP)
SET_AUTO_NEG_OFF = CommandTemplate('port-config-modify port {port_id} no-autoneg', ACTION_MAP, ERROR_MAP)
PHYS_TO_LOGICAL = CommandTemplate('bezel-portmap-show format bezel-intf,port parsable-delim ":"', ACTION_MAP,
                                  ERROR_MAP)
FABRIC_INFO = CommandTemplate('fabric-info parsable-delim ":"', ACTION_MAP, ERROR_MAP)
TUNNEL_INFO = CommandTemplate(
    'tunnel-show auto-tunnel static format switch,name,local-ip,remote-ip, parsable-delim ":"', ACTION_MAP, ERROR_MAP)
VLAN_SHOW = CommandTemplate('vlan-show format switch,id,vxlan,description, parsable-delim ":"', ACTION_MAP, ERROR_MAP)
