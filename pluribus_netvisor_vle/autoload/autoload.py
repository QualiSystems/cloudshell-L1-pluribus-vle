from cloudshell.layer_one.core.response.resource_info.entities.blade import Blade
from cloudshell.layer_one.core.response.resource_info.entities.chassis import Chassis
from pluribus_netvisor_vle.autoload.vw_port import VWPort


class Autoload(object):
    def __init__(self, resource_address, fabric_name, board_table, ports_table, associations_table, logger):
        self._logger = logger
        self._board_table = board_table
        self._ports_table = ports_table
        self._resource_address = resource_address
        self._associations_table = associations_table

        self._chassis_id = '1'
        self._blade_id = '1'

    def _build_fabric(self):
        chassis_dict = {}

        serial_number = self._board_table.get('chassis-serial')
        model_name = self._board_table.get('model')
        sw_version = self._board_table.get('version')
        chassis = Chassis(self._chassis_id, self._resource_address, 'Pluribus Virtual Wire Chassis', serial_number)
        chassis.set_model_name(model_name)
        chassis.set_serial_number(serial_number)
        chassis.set_os_version(sw_version)
        chassis_dict[self._chassis_id] = chassis
        return chassis_dict

    def build_blade(self, chassis_dict):
        blade_model = 'Virtal Wire Module'
        blade = Blade(self._blade_id)
        blade.set_model_name(blade_model)
        blade.set_parent_resource(chassis_dict.get(self._chassis_id))
        return {self._blade_id: blade}

    def _build_ports(self, blades_dict):
        ports_dict = {}
        blade = blades_dict.get(self._blade_id)
        for port_id, port_record in self._ports_table.iteritems():
            speed = port_record.get('speed')
            # autoneg = port_record.get('autoneg')
            phys_id = port_record.get('phys_id')
            port = VWPort(port_id, phys_id)
            port.set_model_name('{} Port'.format(self._board_table.get('model')))
            # port.set_auto_negotiation(autoneg == 'on')
            # port.set_protocol_type_by_speed(speed)
            # port.set_protocol('80')
            port.set_port_speed(speed)
            port.set_parent_resource(blade)
            ports_dict[port_id] = port
        return ports_dict

    def _build_mappings(self, ports_dict):
        for slave_port_id, master_port_id in self._associations_table.iteritems():
            slave_port = ports_dict.get(slave_port_id)
            master_port = ports_dict.get(master_port_id)
            if slave_port and master_port:
                slave_port.add_mapping(master_port)

    def build_structure(self):
        chassis_dict = self._build_chassis()
        blades_dict = self.build_blade(chassis_dict)
        ports_dict = self._build_ports(blades_dict)
        self._build_mappings(ports_dict)
        return chassis_dict.values()
