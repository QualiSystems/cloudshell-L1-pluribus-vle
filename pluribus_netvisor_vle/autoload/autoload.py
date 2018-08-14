from pluribus_netvisor_vle.autoload.vle_blade import VLEBlade
from pluribus_netvisor_vle.autoload.vle_fabric import VLEFabric
from pluribus_netvisor_vle.autoload.vle_port import VLEPort


class Autoload(object):
    def __init__(self, resource_address, fabric_name, fabric_id, nodes_table, ports_table, associations_table, logger):
        self._logger = logger
        self._fabric_name = fabric_name
        self._fabric_id = fabric_id
        self._nodes_table = nodes_table
        self._ports_table = ports_table
        self._resource_address = resource_address
        self._associations_table = associations_table

    def _build_fabric(self):
        fabric = VLEFabric(self._fabric_name, self._resource_address, self._fabric_id)
        fabric.set_fabric_name(self._fabric_name)
        fabric.set_serial_number(self._fabric_id)
        return fabric

    def build_fabric_nodes(self, fabric):
        nodes_dict = {}
        for nodename, node_data in self._nodes_table.iteritems():
            node = VLEBlade(nodename)
            node.set_model_name(node_data.get('model'))
            node.set_serial_number(node_data.get('chassis-serial'))
            node.set_parent_resource(fabric)
            nodes_dict[nodename] = node
        return nodes_dict

    def _build_ports(self, nodes_dict):
        ports_dict = {}
        for node_id, ports_data in self._ports_table.iteritems():
            fabric_node = nodes_dict.get(node_id)
            ports_dict.update(self._build_ports_for_node(fabric_node, ports_data))
        return ports_dict

    def _build_ports_for_node(self, fabric_node, ports_data):
        """
        Ports for fabric node
        :type fabric_node: pluribus_netvisor_vle.autoload.vle_blade.VLEBlade
        :type ports_data: dict
        :rtype: dict
        """
        ports_dict = {}

        for port_id, port_record in ports_data.iteritems():
            speed = port_record.get('speed')
            autoneg = port_record.get('autoneg')
            phys_id = port_record.get('phys_id')

            port = VLEPort(port_id, phys_id)
            port.set_model_name('{} Port'.format(fabric_node.get_model_name()))
            port.set_auto_negotiation(autoneg == 'on')
            # port.set_protocol_type_by_speed(speed)
            # port.set_protocol('80')
            port.set_port_speed(speed)
            port.set_parent_resource(fabric_node)
            ports_dict[(fabric_node.resource_id, port_id)] = port
        return ports_dict

    def _build_mappings(self, ports_dict):
        for slave_port_id, master_port_id in self._associations_table.iteritems():
            slave_port = ports_dict.get(slave_port_id)
            master_port = ports_dict.get(master_port_id)
            if slave_port and master_port:
                slave_port.add_mapping(master_port)

    def build_structure(self):
        fabric = self._build_fabric()
        nodes_dict = self.build_fabric_nodes(fabric)
        ports_dict = self._build_ports(nodes_dict)
        self._build_mappings(ports_dict)
        return [fabric]
