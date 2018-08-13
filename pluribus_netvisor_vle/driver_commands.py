#!/usr/bin/python
# -*- coding: utf-8 -*-

from cloudshell.layer_one.core.driver_commands_interface import DriverCommandsInterface
from cloudshell.layer_one.core.layer_one_driver_exception import LayerOneDriverException
from cloudshell.layer_one.core.response.response_info import GetStateIdResponseInfo, ResourceDescriptionResponseInfo, \
    AttributeValueResponseInfo
from pluribus_netvisor_vle.autoload.autoload import Autoload
from pluribus_netvisor_vle.cli.vw_cli_handler import VWCliHandler
from pluribus_netvisor_vle.command_actions.actions_helper import ActionsManager
from pluribus_netvisor_vle.command_actions.autoload_actions import AutoloadActions
from pluribus_netvisor_vle.command_actions.mapping_actions import MappingActions
from pluribus_netvisor_vle.command_actions.system_actions import SystemActions


class DriverCommands(DriverCommandsInterface):
    """
    Driver commands implementation
    """

    def __init__(self, logger):
        """
        :param logger:
        :type logger: logging.Logger
        """
        self._logger = logger
        self._cli_handler = VWCliHandler(self._logger)

        self._fabric_name = None
        self._fabric_nodes = []

        self.__mapping_actions = None
        self.__system_actions = None

    @property
    def _mapping_actions(self):
        if not self.__mapping_actions:
            self.__mapping_actions = MappingActions(None, self._logger)
        return self.__mapping_actions

    @property
    def _system_actions(self):
        if not self.__system_actions:
            self.__system_actions = SystemActions(None, self._logger)
        return self.__system_actions

    def login(self, address, username, password):
        """
        Perform login operation on the device
        :param address: resource address, "192.168.42.240"
        :param username: username to login on the device
        :param password: password
        :return: None
        :raises Exception: if command failed
        Example:
            # Define session attributes
            self._cli_handler.define_session_attributes(address, username, password)

            # Obtain cli session
            with self._cli_handler.default_mode_service() as session:
                # Executing simple command
                device_info = session.send_command('show version')
                self._logger.info(device_info)
        """
        self._cli_handler.define_session_attributes(address, username, password)
        with self._cli_handler.default_mode_service() as cli_service:
            system_actions = SystemActions(cli_service, self._logger)
            self._fabric_name = system_actions.get_fabric_name()
            if not self._fabric_name:
                raise Exception(self.__class__.__name__, "Fabric is not defined")
            # self._fabric_nodes = system_actions.get_fabric_nodes(self._fabric_name)
            self._logger.info('Fabric name: ' + self._fabric_name)
            # self._logger.info(autoload_actions.board_table())
            self.__mapping_actions = None
            self.__system_actions = None

    def get_state_id(self):
        """
        Check if CS synchronized with the device.
        :return: Synchronization ID, GetStateIdResponseInfo(-1) if not used
        :rtype: cloudshell.layer_one.core.response.response_info.GetStateIdResponseInfo
        :raises Exception: if command failed

        Example:
            # Obtain cli session
            with self._cli_handler.default_mode_service() as session:
                # Execute command
                chassis_name = session.send_command('show chassis name')
                return chassis_name
        """
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._system_actions, session) as system_actions:
                return GetStateIdResponseInfo(system_actions.get_state_id())

    def set_state_id(self, state_id):
        """
        Set synchronization state id to the device, called after Autoload or SyncFomDevice commands
        :param state_id: synchronization ID
        :type state_id: str
        :return: None
        :raises Exception: if command failed

        Example:
            # Obtain cli session
            with self._cli_handler.config_mode_service() as session:
                # Execute command
                session.send_command('set chassis name {}'.format(state_id))
        """
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._system_actions, session) as system_actions:
                system_actions.set_state_id(state_id)

    def map_bidi(self, src_port, dst_port):
        """
        Create a bidirectional connection between source and destination ports
        :param src_port: src port address, '192.168.42.240/1/21'
        :type src_port: str
        :param dst_port: dst port address, '192.168.42.240/1/22'
        :type dst_port: str
        :return: None
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                session.send_command('map bidir {0} {1}'.format(convert_port(src_port), convert_port(dst_port)))

        """
        self._logger.info('MapBidi, SrcPort: {0}, DstPort: {1}'.format(src_port, dst_port))
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._mapping_actions, session) as mapping_actions:
                src_logical_port = self._convert_port_address(src_port)
                dst_logical_port = self._convert_port_address(dst_port)
                mapping_actions.map_bidi(src_logical_port, dst_logical_port)

    def map_uni(self, src_port, dst_ports):
        """
        Unidirectional mapping of two ports
        :param src_port: src port address, '192.168.42.240/1/21'
        :type src_port: str
        :param dst_ports: list of dst ports addresses, ['192.168.42.240/1/22', '192.168.42.240/1/23']
        :type dst_ports: list
        :return: None
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                for dst_port in dst_ports:
                    session.send_command('map {0} also-to {1}'.format(convert_port(src_port), convert_port(dst_port)))
        """
        self._logger.info('MapUni, SrcPort: {0}, DstPorts: {1}'.format(src_port, ','.join(dst_ports)))
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._mapping_actions, session) as mapping_actions:
                mapping_actions.map_uni(self._convert_port_address(src_port),
                                        [self._convert_port_address(port) for port in dst_ports])

    def get_resource_description(self, address):
        """
        Auto-load function to retrieve all information from the device
        :param address: resource address, '192.168.42.240'
        :type address: str
        :return: resource description
        :rtype: cloudshell.layer_one.core.response.response_info.ResourceDescriptionResponseInfo
        :raises cloudshell.layer_one.core.layer_one_driver_exception.LayerOneDriverException: Layer one exception.

        Example:

            from cloudshell.layer_one.core.response.resource_info.entities.chassis import Chassis
            from cloudshell.layer_one.core.response.resource_info.entities.blade import Blade
            from cloudshell.layer_one.core.response.resource_info.entities.port import Port

            chassis_resource_id = chassis_info.get_id()
            chassis_address = chassis_info.get_address()
            chassis_model_name = "Virtual Wire Chassis"
            chassis_serial_number = chassis_info.get_serial_number()
            chassis = Chassis(resource_id, address, model_name, serial_number)

            blade_resource_id = blade_info.get_id()
            blade_model_name = 'Generic L1 Module'
            blade_serial_number = blade_info.get_serial_number()
            blade.set_parent_resource(chassis)

            port_id = port_info.get_id()
            port_serial_number = port_info.get_serial_number()
            port = Port(port_id, 'Generic L1 Port', port_serial_number)
            port.set_parent_resource(blade)

            return ResourceDescriptionResponseInfo([chassis])
        """
        self._logger.info('GetResourceDescriprion for: {}'.format(address))
        with self._cli_handler.default_mode_service() as session:
            autoload_actions = AutoloadActions(session, self._logger)
            nodes_table = autoload_actions.fabric_nodes_table(self._fabric_name)
            ports_table = {node: autoload_actions.ports_table(node) for node in nodes_table}
            print(nodes_table)
            # ports_table = autoload_actions.ports_table()
            # association_table = autoload_actions.associations_table()
            # autoload_helper = Autoload(address, boart_table, ports_table, association_table, self._logger)
            # return ResourceDescriptionResponseInfo(autoload_helper.build_structure())

    def map_clear(self, ports):
        """
        Remove simplex/multi-cast/duplex connection ending on the destination port
        :param ports: ports, ['192.168.42.240/1/21', '192.168.42.240/1/22']
        :type ports: list
        :return: None
        :raises Exception: if command failed

        Example:
            exceptions = []
            with self._cli_handler.config_mode_service() as session:
                for port in ports:
                    try:
                        session.send_command('map clear {}'.format(convert_port(port)))
                    except Exception as e:
                        exceptions.append(str(e))
                if exceptions:
                    raise Exception('self.__class__.__name__', ','.join(exceptions))
        """
        self._logger.info('MapClear, Ports: {}'.format(','.join(ports)))
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._mapping_actions, session) as mapping_actions:
                mapping_actions.map_clear([self._convert_port_address(port) for port in ports])

    def map_clear_to(self, src_port, dst_ports):
        """
        Remove simplex/multi-cast/duplex connection ending on the destination port
        :param src_port: src port address, '192.168.42.240/1/21'
        :type src_port: str
        :param dst_ports: list of dst ports addresses, ['192.168.42.240/1/21', '192.168.42.240/1/22']
        :type dst_ports: list
        :return: None
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                _src_port = convert_port(src_port)
                for port in dst_ports:
                    _dst_port = convert_port(port)
                    session.send_command('map clear-to {0} {1}'.format(_src_port, _dst_port))
        """
        self._logger.info('MapClearTo, SrcPort: {0}, DstPorts: {1}'.format(src_port, ','.join(dst_ports)))
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._mapping_actions, session) as mapping_actions:
                mapping_actions.map_clear_to(self._convert_port_address(src_port),
                                             [self._convert_port_address(port) for port in dst_ports])

    def get_attribute_value(self, cs_address, attribute_name):
        """
        Retrieve attribute value from the device
        :param cs_address: address, '192.168.42.240/1/21'
        :type cs_address: str
        :param attribute_name: attribute name, "Port Speed"
        :type attribute_name: str
        :return: attribute value
        :rtype: cloudshell.layer_one.core.response.response_info.AttributeValueResponseInfo
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                command = AttributeCommandFactory.get_attribute_command(cs_address, attribute_name)
                value = session.send_command(command)
                return AttributeValueResponseInfo(value)
        """
        if attribute_name == 'Serial Number':
            if len(cs_address.split('/')) == 1:
                with self._cli_handler.default_mode_service() as session:
                    autoload_actions = AutoloadActions(session, self._logger)
                    board_table = autoload_actions.board_table()
                    return AttributeValueResponseInfo(board_table.get('chassis-serial'))
            else:
                return AttributeValueResponseInfo('NA')
        else:
            raise LayerOneDriverException(self.__class__.__name__, 'GetAttributeValue command is not supported')

    def set_attribute_value(self, cs_address, attribute_name, attribute_value):
        """
        Set attribute value to the device
        :param cs_address: address, '192.168.42.240/1/21'
        :type cs_address: str
        :param attribute_name: attribute name, "Port Speed"
        :type attribute_name: str
        :param attribute_value: value, "10000"
        :type attribute_value: str
        :return: attribute value
        :rtype: cloudshell.layer_one.core.response.response_info.AttributeValueResponseInfo
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                command = AttributeCommandFactory.set_attribute_command(cs_address, attribute_name, attribute_value)
                session.send_command(command)
                return AttributeValueResponseInfo(attribute_value)
        """
        if attribute_name == 'Auto Negotiation':
            with self._cli_handler.default_mode_service() as session:
                with ActionsManager(self._system_actions, session) as system_actions:
                    system_actions.set_auto_negotiation(self._convert_port_address(cs_address), attribute_value)
        else:
            raise LayerOneDriverException(self.__class__.__name__,
                                          'SetAttributeValue for address {} is not supported'.format(cs_address))

    def map_tap(self, src_port, dst_ports):
        self._logger.info('MapTap, SrcPort: {0}, DstPorts: {1}'.format(src_port, ','.join(dst_ports)))
        with self._cli_handler.default_mode_service() as session:
            with ActionsManager(self._mapping_actions, session) as mapping_actions:
                mapping_actions.map_tap(self._convert_port_address(src_port),
                                        [self._convert_port_address(port) for port in dst_ports])

    def set_speed_manual(self, src_port, dst_port, speed, duplex):
        """
        Set connection speed. Is not used with the new standard
        :param src_port:
        :param dst_port:
        :param speed:
        :param duplex:
        :return:
        """
        pass

    @staticmethod
    def _convert_port_address(port):
        """
        :param port:
        :type port: str
        :return:
        """
        return port.split('/')[-1]
