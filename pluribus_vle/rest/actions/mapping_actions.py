from pluribus_vle.rest.api_handler import PluribusApiException


class RestMappingActions(object):
    """ Mapping actions. """
    PORTS = "ports"
    BIDIR = "bidir"
    MONITOR_PORTS = "monitor_ports"
    FORBIDDEN_PORT_STATUS_TABLE = ["pn-fabric", "pn-cluster", "pn-internal", "vle",
                                   "vxlan-loopback", "disabled"]

    def __init__(self, api, switch_mapping, logger):
        self._api = api
        self._switch_mapping = switch_mapping
        self._logger = logger

        self.__associations_table = None
        self.__phys_to_logical_table = None

    def map_bidi_multi_node(self, src_node, dst_node, src_port, dst_port, src_tunnel,
                            dst_tunnel, vlan_id, vle_name):
        """ Create BiDirectional connection on multiple nodes. """
        src_node_id = self._switch_mapping.get(src_node, "fabric")
        dst_node_id = self._switch_mapping.get(dst_node, "fabric")
        self._validate_port(src_node, src_port)
        self._validate_port(dst_node, dst_port)

        self._create_vlan(src_node, src_port, vlan_id)
        self._api.add_vxlan_to_tunnel(
            tunnel_name=src_tunnel,
            vxlan_id=vlan_id,
            hostid=src_node_id
        )
        self._validate_vxlan_add(src_node, vlan_id, src_tunnel)

        self._create_vlan(dst_node, dst_port, vlan_id)
        self._api.add_vxlan_to_tunnel(
            tunnel_name=dst_tunnel,
            vxlan_id=vlan_id,
            hostid=dst_node_id
        )
        self._validate_vxlan_add(dst_node, vlan_id, dst_tunnel)

        self._api.create_vles(
            vle_name=vle_name,
            node_1=src_node_id,
            node_1_port=src_port,
            node_2=dst_node_id,
            node_2_port=dst_port
        )
        self._validate_vle_creation(vle_name)

    def map_bidi_single_node(self, node, src_port, dst_port, vlan_id, vle_name):
        """ Create BiDirectional connection on single node. """
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
            node_2_port=dst_port
        )
        self._validate_vle_creation(vle_name)

    def delete_single_node_vle(self, node, vle_name, vlan_id):
        """ Delete VLE on single node. """
        self._api.delete_vles(vle_name=vle_name)
        self._validate_vle_deletion(vle_name)

        self._api.delete_vlan(
            vlan_id=vlan_id,
            hostid=self._switch_mapping.get(node, "fabric")
        )
        self._validate_vlan_id_deletion(node, vlan_id)

    def delete_multi_node_vle(self, src_node, dst_node, vle_name, vlan_id):
        """ Delete VLE on multiple nodes. """
        self._api.delete_vles(vle_name=vle_name)
        self._validate_vle_deletion(vle_name)
        self._api.delete_vlan(
            vlan_id=vlan_id,
            hostid=self._switch_mapping.get(src_node, "fabric")
        )
        self._validate_vlan_id_deletion(src_node, vlan_id)
        self._api.delete_vlan(
            vlan_id=vlan_id,
            hostid=self._switch_mapping.get(dst_node, "fabric")
        )
        self._validate_vlan_id_deletion(dst_node, vlan_id)

    def connection_table(self):
        """ Build connection table. """
        connection_table = {}
        data = self._api.get_vles()
        for vle in data:
            src_record = (vle["node1-name"], vle["node-1-port"])
            dst_record = (vle["node2-name"], vle["node-2-port"])
            vle_name = vle["name"]
            connection_table[src_record] = (dst_record, vle_name)
            connection_table[dst_record] = (src_record, vle_name)
        return connection_table

    def _create_vlan(self, node, port, vlan_id):
        """ Create VLAN. """
        self._remove_port_from_vlans(node, port)
        self._validate_port_is_not_a_member(node, port)

        self._api.create_vlan(
            vlan_id=vlan_id,
            vxlan_id=vlan_id,
            port=port,
            hostid=self._switch_mapping.get(node, "fabric")
        )
        self._validate_port_is_a_member(node, port, vlan_id)

    def _add_to_vlan(self, node, port, vlan_id):
        """ Add port to VLAN. """
        self._remove_port_from_vlans(node, port)
        self._validate_port_is_not_a_member(node, port)

        self._api.add_ports_to_vlan(
            vlan_id=vlan_id,
            port=port,
            hostid=self._switch_mapping.get(node, "fabric")
        )
        self._validate_port_is_a_member(node, port, vlan_id)

    def _validate_port_is_not_a_member(self, node, port):
        """  """
        vlan_members = self.vlan_ids_for_port(node, port)
        if vlan_members and len(set(vlan_members) - {1}) > 0:
            raise PluribusApiException(
                "Port {} already a member of vlan_id {}".format(
                    (node, port),
                    vlan_members)
            )

    def _validate_port_is_a_member(self, node, port, vlan_id):
        """  """
        vlan_members = self.vlan_ids_for_port(node, port)
        if not vlan_members or int(vlan_id) not in vlan_members:
            raise PluribusApiException(
                "Cannot add port {} to vlan {}".format((node, port), vlan_id)
            )

    def _validate_vxlan_add(self, node_name, vxlan_id, tunnel):
        """ Validate VXLAN is exists. """
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.get_tunnel_vxlans(tunnel=tunnel, hostid=node_id)

        for vxlan in data:
            if vxlan.get("vxlan", -1) == vxlan_id:
                return

        raise PluribusApiException(
            "Failed to add vxlan {} to tunnel {},"
            "see driver logs for more details".format(vxlan_id, tunnel))

    def _validate_vle_creation(self, vle_name):
        """ Validate is VLE created successfully. """
        data = self._api.get_vle_by_name(vle_name=vle_name)

        if not data or data[0].get("name") != vle_name:
            raise PluribusApiException(
                "VLE {} creation failed, see logs for more details".format(vle_name))

    def _validate_vle_deletion(self, vle_name):
        """ Validate is VLE deleted successfully. """
        data = self._api.get_vle_by_name(vle_name=vle_name)
        if data:
            raise PluribusApiException(
                "Failed to delete VLE {}, see logs for more details".format(vle_name))

    def _validate_vlan_id_deletion(self, node_name, vlan_id):
        """ Validate is VLAN deleted successfully. """
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.get_vlan(vlan_id=vlan_id, hostid=node_id)
        if data:
            raise PluribusApiException(
                "Failed to delete vlan {} on node {}".format(vlan_id, node_name)
            )

    def vlan_ids_for_port(self, node, port):
        """ Get all VLANs for port. """
        node_id = self._switch_mapping.get(node, "fabric")
        data = self._api.get_port_vlan_info(port=port, hostid=node_id)

        if data and data[0].get("vlans", ""):
            return map(int, data[0].get("vlans", "").split(","))

    def _validate_port(self, node_name, port):
        """ Validate port. """
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.get_port_status(port=port, hostid=node_id)

        if data:
            status_data = data[0].get("status")
            if status_data:
                for status in status_data.split(","):
                    if status.strip().lower() in self.FORBIDDEN_PORT_STATUS_TABLE:
                        raise PluribusApiException(
                            "Port {} is not allowed to use for VLE,"
                            "it has status {}".format((node_name, port), status)
                        )

    def _remove_from_vlan(self, node_name, vlan_id, port):
        """ Remove port from VLAN. """
        node_id = self._switch_mapping.get(node_name, "fabric")
        data = self._api.delete_ports_from_vlan(
            vlan_id=vlan_id,
            ports=port,
            hostid=node_id
        )

        if "removed" not in data.lower():
            raise PluribusApiException(
                "Cannot remove port {} from VlanId {} on node {}".format(
                    port,
                    vlan_id,
                    node_name
                )
            )

    def _remove_port_from_vlans(self, node, port):
        """ Remove port from VLANs. """
        vlan_members = self.vlan_ids_for_port(node, port)
        if vlan_members is not None:
            for vlan_id in vlan_members:
                self._remove_from_vlan(node, vlan_id, port)
