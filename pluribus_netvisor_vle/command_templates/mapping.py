from collections import OrderedDict

from cloudshell.cli.command_template.command_template import CommandTemplate

ACTION_MAP = OrderedDict()
ERROR_MAP = OrderedDict([(r'[Ee]rror:', 'Command error'), (r'[Cc]onflict', 'Port conflict'),
                         (r'[Pp]ort\s[Aa]ssoc\w*ation\s.+\salready\sexists', 'Port association already exists'),
                         (r'[Uu]nable to find port-association to delete',
                          'Unable to find port-association to delete')])

CREATE_VLAN = CommandTemplate(
    'switch {node_name} vlan-create id {vlan_id} scope local vxlan-mode transparent vxlan {vxlan_id} ports {port}',
    ACTION_MAP, ERROR_MAP)
ADD_TO_VLAN = CommandTemplate('switch {node_name} vlan-port-add vlan-id {vlan_id} ports {port}', ACTION_MAP, ERROR_MAP)
ADD_VXLAN_TO_TUNNEL = CommandTemplate('switch {node_name} tunnel-vxlan-add name {tunnel_name} vxlan {vxlan_id}',
                                      ACTION_MAP, ERROR_MAP)
VLE_CREATE = CommandTemplate(
    'vle-create name {vle_name} node-1 {node_1} node-1-port {node_1_port} node-2 {node_2} node-2-port {node_2_port} tracking',
    ACTION_MAP, ERROR_MAP)

DELETE_VLE = CommandTemplate('vle-delete name {vle_name}', ACTION_MAP, ERROR_MAP)
DELETE_VLAN = CommandTemplate('switch {node} vlan-delete id {vlan_id}', ACTION_MAP, ERROR_MAP)

VLE_SHOW = CommandTemplate('vle-show format name,node-1,node-2,node-1-port,node-2-port, parsable-delim ":"', ACTION_MAP,
                           ERROR_MAP)

PORT_VLAN_INFO = CommandTemplate(
    'switch {node} port-vlan-show ports {port} format switch,port,vlans parsable-delim ":"',
    ACTION_MAP, ERROR_MAP)

VLE_SHOW_FOR_NAME = CommandTemplate(
    'vle-show name {vle_name} format name,node-1,node-2,node-1-port,node-2-port,status, parsable-delim ":"', ACTION_MAP,
    ERROR_MAP)

VXLAN_SHOW = CommandTemplate('switch {node_name} tunnel-vxlan-show vxlan {vxlan_id} parsable-delim ":"', ACTION_MAP,
                             ERROR_MAP)

VLAN_SHOW = CommandTemplate('switch {node_name} vlan-show id {vlan_id} format id,switch,vxlan parsable-delim ":"',
                            ACTION_MAP, ERROR_MAP)
