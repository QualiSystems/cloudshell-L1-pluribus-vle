#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

from cloudshell.layer_one.core.driver_commands_interface import DriverCommandsInterface
from cloudshell.layer_one.core.layer_one_driver_exception import LayerOneDriverException
from cloudshell.layer_one.core.response.response_info import GetStateIdResponseInfo, \
    ResourceDescriptionResponseInfo, \
    AttributeValueResponseInfo
from pluribus_vle.autoload.autoload import Autoload
from pluribus_vle.cli.vw_cli_handler import VWCliHandler
from pluribus_vle.command_actions.autoload_actions import AutoloadActions
from pluribus_vle.command_actions.mapping_actions import MappingActions
from pluribus_vle.command_actions.system_actions import SystemActions

from pluribus_vle.rest.api_handler import PluribusRESTAPI
from pluribus_vle.rest.actions.autoload_actions import RestAutoloadActions
from pluribus_vle.rest.actions.mapping_actions import RestMappingActions
from pluribus_vle.rest.actions.system_actions import RestSystemActions


class DriverCommands(DriverCommandsInterface):
    """ Driver commands implementation. """

    def __init__(self, logger, runtime_config):
        """
        :type logger: logging.Logger
        :type runtime_config: cloudshell.layer_one.core.helper.runtime_configuration.RuntimeConfiguration
        """
        self._logger = logger
        self._vlan_min = runtime_config.read_key("DRIVER.VLAN_MIN", 100)
        self._vlan_max = runtime_config.read_key("DRIVER.VLAN_MAX", 4000)
        self._vle_prefix = runtime_config.read_key("DRIVER.VLE_PREFIX", "QSVLE-")
        self._map_on_set_vlan = runtime_config.read_key("DRIVER.MAP_ON_SET_VLAN", False)

        self._rest_api_enabled = runtime_config.read_key("API.REST.ENABLE", True)
        if self._rest_api_enabled:
            self._rest_scheme = runtime_config.read_key("API.REST.TYPE", "http")
            self._rest_port = int(runtime_config.read_key("API.REST.PORT", 80))
        self._rest_api = None
        self._switch_mapping = None

        self._cli_handler = VWCliHandler(self._logger)

        self._fabric_name = None
        self._fabric_id = None
        self._fabric_nodes = None
        self._tunnels_table = {}

        self.__mapping_actions = None
        self.__system_actions = None

        # Used to store map requests
        self._map_requests = {}
        # Used to store vlanId"s attached to port
        self._vlan_table = {}

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
        """ Perform login operation on the device.

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
                device_info = session.send_command("show version")
                self._logger.info(device_info)
        """
        # REST Implementation
        if self._rest_api_enabled:
            self._rest_api = PluribusRESTAPI(
                address=address,
                username=username,
                password=password,
                scheme=self._rest_scheme,
                port=self._rest_port,
            )

            system_actions = RestSystemActions(api=self._rest_api, logger=self._logger)
            fabric_info = system_actions.get_fabric_info()

            self._fabric_name = fabric_info.get("name")
            self._fabric_id = fabric_info.get("id")
            if not self._fabric_name:
                raise LayerOneDriverException("Fabric is not defined")
            self._logger.info("Fabric name: " + self._fabric_name)
            self._tunnels_table = system_actions.tunnels_table()
            self._switch_mapping = system_actions.get_switch_mapping()
            return

        # CLI Implementation
        self._cli_handler.define_session_attributes(address, username, password)
        with self._cli_handler.default_mode_service() as cli_service:
            system_actions = SystemActions(cli_service, self._logger)
            fabric_info = system_actions.get_fabric_info()
            self._fabric_name = fabric_info.get("name")
            self._fabric_id = fabric_info.get("id")
            if not self._fabric_name:
                raise LayerOneDriverException("Fabric is not defined")
            self._logger.info("Fabric name: " + self._fabric_name)
            self._tunnels_table = system_actions.tunnels_table()
            self.__mapping_actions = None
            self.__system_actions = None

    def get_resource_description(self, address):
        """ Auto-load function to retrieve all information from the device.

        :param address: resource address, "192.168.42.240"
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
            blade_model_name = "Generic L1 Module"
            blade_serial_number = blade_info.get_serial_number()
            blade.set_parent_resource(chassis)

            port_id = port_info.get_id()
            port_serial_number = port_info.get_serial_number()
            port = Port(port_id, "Generic L1 Port", port_serial_number)
            port.set_parent_resource(blade)

            return ResourceDescriptionResponseInfo([chassis])
        """
        self._logger.info("GetResourceDescription for: {}".format(address))

        # REST Implementation
        if self._rest_api_enabled and self._rest_api:
            autoload_actions = RestAutoloadActions(
                api=self._rest_api,
                switch_mapping=self._switch_mapping,
                logger=self._logger)
            nodes_table = autoload_actions.fabric_nodes_table(self._fabric_name)
            ports_table = {node: autoload_actions.ports_table(node) for node in
                           nodes_table}
            associations_table = autoload_actions.associations_table()

        else:
            # CLI Implementation
            with self._cli_handler.default_mode_service() as session:
                autoload_actions = AutoloadActions(session, self._logger)
                nodes_table = autoload_actions.fabric_nodes_table(self._fabric_name)
                ports_table = {node: autoload_actions.ports_table(node) for node in
                               nodes_table}
                associations_table = autoload_actions.associations_table()

        autoload_helper = Autoload(address, self._fabric_name, self._fabric_id,
                                   nodes_table, ports_table,
                                   associations_table,
                                   self._logger)
        return ResourceDescriptionResponseInfo(autoload_helper.build_structure())

    def map_uni(self, src_port, dst_ports):
        """ Unidirectional mapping of two ports.

        :param src_port: src port address, "192.168.42.240/1/21"
        :type src_port: str
        :param dst_ports: list of dst ports addresses, ["192.168.42.240/1/22", "192.168.42.240/1/23"]
        :type dst_ports: list
        :return: None
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                for dst_port in dst_ports:
                    session.send_command("map {0} also-to {1}".format(convert_port(src_port), convert_port(dst_port)))
        """
        raise LayerOneDriverException("This driver does not support MapUni command")

    def map_bidi(self, src_port, dst_port, vlan_id=None):
        """ Create a bidirectional connection between source and destination ports.

        :param src_port: src port address, "192.168.42.240/1/21"
        :type src_port: str
        :param dst_port: dst port address, "192.168.42.240/1/22"
        :type dst_port: str
        :param vlan_id: VLAN id, 1414
        :type vlan_id: int
        :return: None
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                session.send_command("map bidir {0} {1}".format(convert_port(src_port),
                                                                convert_port(dst_port)))

        """
        if self._map_on_set_vlan is True:
            if vlan_id is None:
                self._map_requests[src_port] = dst_port
                self._map_requests[dst_port] = src_port
                return

        self._logger.info(
            "MapBidi, SrcPort: {0}, DstPort: {1}".format(src_port, dst_port))

        src_node, src_port = self._convert_port_address(src_port)
        dst_node, dst_port = self._convert_port_address(dst_port)

        # REST Implementation
        if self._rest_api_enabled and self._rest_api:
            system_actions = RestSystemActions(api=self._rest_api, logger=self._logger)
            mapping_actions = RestMappingActions(
                api=self._rest_api,
                switch_mapping=self._switch_mapping,
                logger=self._logger)

            if vlan_id is None:
                vlan_id = system_actions.get_available_vlan_id(self._vlan_min,
                                                               self._vlan_max)
            else:
                vlan_id = system_actions.get_available_vlan_id(int(vlan_id),
                                                               int(vlan_id))
            vle_name = self._vle_prefix + str(vlan_id)

            system_actions.set_port_state(
                src_port,
                self._switch_mapping.get(src_node, "fabric"),
                "enable"
            )
            system_actions.set_port_state(
                dst_port,
                self._switch_mapping.get(dst_node, "fabric"),
                "enable"
            )

            if src_node == dst_node:
                mapping_actions.map_bidi_single_node(src_node, src_port, dst_port,
                                                     vlan_id, vle_name)
            else:
                src_tunnel = self._tunnels_table.get((src_node, dst_node))
                dst_tunnel = self._tunnels_table.get((dst_node, src_node))
                if src_tunnel and dst_tunnel:
                    mapping_actions.map_bidi_multi_node(src_node, dst_node,
                                                        src_port, dst_port,
                                                        src_tunnel, dst_tunnel,
                                                        vlan_id, vle_name)
                else:
                    raise LayerOneDriverException(
                        "Cannot find the appropriate tunnel"
                    )
        else:
            # CLI Implementation
            with self._cli_handler.default_mode_service() as session:
                system_actions = SystemActions(session, self._logger)
                mapping_actions = MappingActions(session, self._logger)

                if vlan_id is None:
                    vlan_id = system_actions.get_available_vlan_id(self._vlan_min,
                                                                   self._vlan_max)
                else:
                    vlan_id = system_actions.get_available_vlan_id(int(vlan_id),
                                                                   int(vlan_id))
                vle_name = self._vle_prefix + str(vlan_id)

                system_actions.set_port_state(src_port, src_node, "enable")
                system_actions.set_port_state(dst_port, dst_node, "enable")

                if src_node == dst_node:
                    mapping_actions.map_bidi_single_node(src_node, src_port, dst_port,
                                                         vlan_id, vle_name)
                else:
                    src_tunnel = self._tunnels_table.get((src_node, dst_node))
                    dst_tunnel = self._tunnels_table.get((dst_node, src_node))
                    if src_tunnel and dst_tunnel:
                        mapping_actions.map_bidi_multi_node(src_node, dst_node,
                                                            src_port, dst_port,
                                                            src_tunnel, dst_tunnel,
                                                            vlan_id, vle_name)
                    else:
                        raise LayerOneDriverException(
                            "Cannot find the appropriate tunnel"
                        )

    def map_clear(self, ports):
        """ Remove simplex/multi-cast/duplex connection ending on the destination port.

        :param ports: ports, ["192.168.42.240/1/21", "192.168.42.240/1/22"]
        :type ports: list
        :return: None
        :raises Exception: if command failed

        Example:
            exceptions = []
            with self._cli_handler.config_mode_service() as session:
                for port in ports:
                    try:
                        session.send_command("map clear {}".format(convert_port(port)))
                    except Exception as e:
                        exceptions.append(str(e))
                if exceptions:
                    raise Exception("self.__class__.__name__", ",".join(exceptions))
        """
        self._logger.info("MapClear, Ports: {}".format(",".join(ports)))
        exception_messages = []

        # REST Implementation
        if self._rest_api_enabled and self._rest_api:
            system_actions = RestSystemActions(api=self._rest_api, logger=self._logger)
            mapping_actions = RestMappingActions(
                api=self._rest_api,
                switch_mapping=self._switch_mapping,
                logger=self._logger)
            for port in ports:
                src_node, src_port = self._convert_port_address(port)
                connection_table = mapping_actions.connection_table()
                dst_record = connection_table.get((src_node, src_port))
                if not dst_record:
                    continue
                (dst_node, dst_port), vle_name = dst_record
                try:
                    vlan_ids = mapping_actions.vlan_ids_for_port(src_node, src_port)
                    vlan_id = self._valid_vlan_id(vlan_ids)
                    if src_node == dst_node:
                        mapping_actions.delete_single_node_vle(src_node, vle_name,
                                                               vlan_id)
                    else:
                        mapping_actions.delete_multi_node_vle(src_node, dst_node,
                                                              vle_name, vlan_id)

                    system_actions.set_port_state(
                        src_port,
                        self._switch_mapping.get(src_node, "fabric"),
                        "disable"
                    )
                    system_actions.set_port_state(
                        dst_port,
                        self._switch_mapping.get(dst_node, "fabric"),
                        "disable"
                    )

                except Exception as e:
                    if len(e.args) > 1:
                        exception_messages.append(e.args[1])
                    elif len(e.args) == 1:
                        exception_messages.append(e.args[0])
            if exception_messages:
                raise LayerOneDriverException(", ".join(exception_messages))

        # CLI Implementation
        else:
            with self._cli_handler.default_mode_service() as session:
                system_actions = SystemActions(session, self._logger)
                mapping_actions = MappingActions(session, self._logger)
                for port in ports:
                    src_node, src_port = self._convert_port_address(port)
                    connection_table = mapping_actions.connection_table()
                    dst_record = connection_table.get((src_node, src_port))
                    if not dst_record:
                        continue
                    (dst_node, dst_port), vle_name = dst_record
                    try:
                        vlan_ids = mapping_actions.vlan_ids_for_port(src_node, src_port)
                        vlan_id = self._valid_vlan_id(vlan_ids)
                        if src_node == dst_node:
                            mapping_actions.delete_single_node_vle(src_node, vle_name,
                                                                   vlan_id)
                        else:
                            mapping_actions.delete_multi_node_vle(src_node, dst_node,
                                                                  vle_name, vlan_id)
                        system_actions.set_port_state(src_port, src_node, "disable")
                        system_actions.set_port_state(dst_port, dst_node, "disable")
                    except Exception as e:
                        if len(e.args) > 1:
                            exception_messages.append(e.args[1])
                        elif len(e.args) == 1:
                            exception_messages.append(e.args[0])
                if exception_messages:
                    raise LayerOneDriverException(", ".join(exception_messages))

    def map_clear_to(self, src_port, dst_ports):
        """ Remove simplex/multi-cast/duplex connection ending on the destination port.

        :param src_port: src port address, "192.168.42.240/1/21"
        :type src_port: str
        :param dst_ports: list of dst ports addresses, ["192.168.42.240/1/21", "192.168.42.240/1/22"]
        :type dst_ports: list
        :return: None
        :raises Exception: if command failed

        Example:
            with self._cli_handler.config_mode_service() as session:
                _src_port = convert_port(src_port)
                for port in dst_ports:
                    _dst_port = convert_port(port)
                    session.send_command("map clear-to {0} {1}".format(_src_port, _dst_port))
        """
        self._logger.info(
            "MapClearTo, SrcPort: {0}, DstPorts: {1}".format(
                src_port, ",".join(dst_ports)
            )
        )
        ports = [src_port]
        ports.extend(dst_ports)
        self.map_clear(ports)

    def map_tap(self, src_port, dst_ports):
        raise LayerOneDriverException("MapTap is not supported")

    def get_attribute_value(self, cs_address, attribute_name):
        """ Retrieve attribute value from the device.

        :param cs_address: address, "192.168.42.240/1/21"
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
        if attribute_name == "Serial Number":
            if len(cs_address.split("/")) == 1:
                return AttributeValueResponseInfo(self._fabric_id)
            else:
                return AttributeValueResponseInfo("NA")
        else:
            raise LayerOneDriverException("GetAttributeValue command is not supported")

    def set_attribute_value(self, cs_address, attribute_name, attribute_value):
        """ Set attribute value to the device.

        :param cs_address: address, "192.168.42.240/1/21"
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
        self._logger.debug(
            "SetAttributeValue, Addr: {0}, Name: {1}, Value: {2}".format(
                cs_address,
                attribute_name,
                attribute_value)
        )

        if attribute_name == "L1 VLAN ID" and self._map_on_set_vlan is True:
            vlan_id = attribute_value
            src_port = self._vlan_table.get(vlan_id)
            if src_port is None:
                self._logger.debug(
                    "Add vlan record {0}-{1}".format(vlan_id, cs_address))
                self._vlan_table[vlan_id] = cs_address
                return

            dst_port = cs_address
            req_dst_port = self._map_requests.get(src_port)
            req_src_port = self._map_requests.get(dst_port)
            self._logger.debug(
                "Call mapping VlanID: {0}, SrcPort: {1}, DstPort: {2}".format(vlan_id,
                                                                              src_port,
                                                                              dst_port))
            if all([req_src_port, req_dst_port]) and {req_src_port, req_dst_port} == {
                src_port, dst_port}:
                self._map_requests.pop(src_port, None)
                self._map_requests.pop(dst_port, None)
                self._vlan_table.pop(vlan_id, None)
                return self.map_bidi(src_port, dst_port, int(vlan_id))

        raise LayerOneDriverException(
            "SetAttributeValue for address {} is not supported".format(cs_address)
        )

    def get_state_id(self):
        """ Check if CS synchronized with the device.

        :return: Synchronization ID, GetStateIdResponseInfo(-1) if not used
        :rtype: cloudshell.layer_one.core.response.response_info.GetStateIdResponseInfo
        :raises Exception: if command failed

        Example:
            # Obtain cli session
            with self._cli_handler.default_mode_service() as session:
                # Execute command
                chassis_name = session.send_command("show chassis name")
                return chassis_name
        """
        return GetStateIdResponseInfo(-1)

    def set_state_id(self, state_id):
        """ Set synchronization state id to the device.
        Called after Autoload or SyncFomDevice commands.

        :param state_id: synchronization ID
        :type state_id: str
        :return: None
        :raises Exception: if command failed

        Example:
            # Obtain cli session
            with self._cli_handler.config_mode_service() as session:
                # Execute command
                session.send_command("set chassis name {}".format(state_id))
        """
        pass

    def set_speed_manual(self, src_port, dst_port, speed, duplex):
        """
        Set connection speed. Is not used with the new standard
        :param src_port:
        :param dst_port:
        :param speed:
        :param duplex:
        :return:
        """
        raise NotImplementedError

    def _valid_vlan_id(self, vlan_ids):
        if vlan_ids:
            for vlan_id in vlan_ids:
                if self._vlan_min <= int(vlan_id) <= self._vlan_max:
                    return vlan_id
        raise LayerOneDriverException(
            "Vlan ids {} is not correct or is not from allocated range".format(vlan_ids)
        )

    @staticmethod
    def _convert_port_address(port):
        """
        :param port:
        :type port: str
        :return:
        """
        return port.split("/")[1:3]
