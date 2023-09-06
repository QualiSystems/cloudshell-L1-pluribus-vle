from __future__ import annotations

from typing import TYPE_CHECKING

from cloudshell.layer_one.core.driver_commands_interface import DriverCommandsInterface
from cloudshell.layer_one.core.helper.logger import get_l1_logger
from cloudshell.layer_one.core.layer_one_driver_exception import LayerOneDriverException
from cloudshell.layer_one.core.response.response_info import (
    AttributeValueResponseInfo,
    GetStateIdResponseInfo,
    ResourceDescriptionResponseInfo,
)

from pluribus_vle.autoload.autoload import Autoload
from pluribus_vle.cli.vw_cli_handler import VWCliHandler
from pluribus_vle.command_actions.autoload_actions import AutoloadActions
from pluribus_vle.command_actions.mapping_actions import MappingActions
from pluribus_vle.command_actions.system_actions import SystemActions
from pluribus_vle.rest.actions.autoload_actions import RestAutoloadActions
from pluribus_vle.rest.actions.mapping_actions import RestMappingActions
from pluribus_vle.rest.actions.system_actions import RestSystemActions
from pluribus_vle.rest.api_handler import PluribusRESTAPI

if TYPE_CHECKING:
    from cloudshell.layer_one.core.helper.runtime_configuration import (
        RuntimeConfiguration,
    )

logger = get_l1_logger(name=__name__)


class DriverCommands(DriverCommandsInterface):
    """Driver commands implementation."""

    def __init__(self, runtime_config: RuntimeConfiguration) -> None:
        self._vlan_min = runtime_config.read_key("DRIVER.VLAN_MIN", 100)
        self._vlan_max = runtime_config.read_key("DRIVER.VLAN_MAX", 4000)
        self._vle_prefix = runtime_config.read_key("DRIVER.VLE_PREFIX", "QSVLE-")
        self._map_on_set_vlan = runtime_config.read_key("DRIVER.MAP_ON_SET_VLAN", False)

        self._rest_api_enabled = runtime_config.read_key("API.REST.ENABLE", True)
        if self._rest_api_enabled:
            self._rest_scheme = runtime_config.read_key("API.REST.TYPE", "http")
            self._rest_port = int(runtime_config.read_key("API.REST.PORT", 80))
        self._rest_api: PluribusRESTAPI | None = None
        self._cli_handler = VWCliHandler()

        self._switch_mapping: dict[str, str] = {}
        self._fabric_name: str = ""
        self._fabric_id: str = ""
        self._tunnels_table: dict = {}

        self.__mapping_actions: MappingActions | None = None
        self.__system_actions: SystemActions | None = None

        # Used to store map requests
        self._map_requests: dict[str, str] = {}
        # Used to store vlanId's attached to port
        self._vlan_table: dict[int, str] = {}

    @property
    def _mapping_actions(self):
        if not self.__mapping_actions:
            self.__mapping_actions = MappingActions(cli_service=None)
        return self.__mapping_actions

    @property
    def _system_actions(self):
        if not self.__system_actions:
            self.__system_actions = SystemActions(cli_service=None)
        return self.__system_actions

    def login(self, address: str, username: str, password: str) -> None:
        """Perform login operation on the device."""
        # REST Implementation
        if self._rest_api_enabled:
            self._rest_api = PluribusRESTAPI(
                address=address,
                username=username,
                password=password,
                scheme=self._rest_scheme,
                port=self._rest_port,
            )
            self._login(system_actions=RestSystemActions(api=self._rest_api))
            return

        # CLI Implementation
        self._cli_handler.define_session_attributes(address, username, password)
        with self._cli_handler.default_mode_service() as cli_service:
            self._login(system_actions=SystemActions(cli_service))
            self.__mapping_actions = None
            self.__system_actions = None

    def _login(self, system_actions: RestSystemActions | SystemActions) -> None:
        fabric_info = system_actions.get_fabric_info()
        self._fabric_name = fabric_info.get("name", "")
        self._fabric_id = fabric_info.get("id", "")
        if not self._fabric_name or not self._fabric_id:
            raise LayerOneDriverException("Fabric is not defined")
        logger.info(f"Fabric name: {self._fabric_name}")
        self._tunnels_table = system_actions.tunnels_table()
        self._switch_mapping = system_actions.get_switch_mapping()

    def get_resource_description(self, address: str) -> ResourceDescriptionResponseInfo:
        """Auto-load function to retrieve all information from the device."""
        logger.info(f"GetResourceDescription for: {address}")

        # REST Implementation
        if self._rest_api_enabled and self._rest_api:
            nodes_table, ports_table, associations_table = self._get_device_info(
                autoload_actions=RestAutoloadActions(
                    api=self._rest_api, switch_mapping=self._switch_mapping
                )
            )

        else:
            # CLI Implementation
            with self._cli_handler.default_mode_service() as session:
                nodes_table, ports_table, associations_table = self._get_device_info(
                    autoload_actions=AutoloadActions(session)
                )

        autoload_helper = Autoload(
            resource_address=address,
            fabric_name=self._fabric_name,
            fabric_id=self._fabric_id,
            nodes_table=nodes_table,
            ports_table=ports_table,
            associations_table=associations_table,
        )
        return ResourceDescriptionResponseInfo(autoload_helper.build_structure())

    def _get_device_info(
        self, autoload_actions: RestAutoloadActions | AutoloadActions
    ) -> tuple[
        dict[str, dict[str, str]],
        dict[str, dict[str, dict[str, str]]],
        dict[tuple[str, str], tuple[str, str]],
    ]:
        nodes_table = autoload_actions.fabric_nodes_table(self._fabric_name)
        ports_table = {node: autoload_actions.ports_table(node) for node in nodes_table}
        associations_table = autoload_actions.associations_table()
        return nodes_table, ports_table, associations_table

    def map_uni(self, src_port: str, dst_ports: list[str]) -> None:
        """Unidirectional mapping of two ports."""
        raise LayerOneDriverException("This driver does not support MapUni command")

    def map_bidi(
        self, src_port: str, dst_port: str, vlan_id: int | None = None
    ) -> None:
        """Create a bidirectional connection between source and destination ports."""
        # REST Implementation
        if self._rest_api_enabled and self._rest_api:
            self._create_map_bidi(
                src_port,
                dst_port,
                vlan_id,
                RestSystemActions(api=self._rest_api),
                RestMappingActions(
                    api=self._rest_api,
                    switch_mapping=self._switch_mapping,
                ),
            )
        else:
            # CLI Implementation
            with self._cli_handler.default_mode_service() as session:
                self._create_map_bidi(
                    src_port,
                    dst_port,
                    vlan_id,
                    SystemActions(session),
                    MappingActions(session),
                )

    def _create_map_bidi(
        self,
        src_port: str,
        dst_port: str,
        vlan_id: int | None,
        system_actions: RestSystemActions | SystemActions,
        mapping_actions: RestMappingActions | MappingActions,
    ) -> None:
        if self._map_on_set_vlan is True:
            if vlan_id is None:
                self._map_requests[src_port] = dst_port
                self._map_requests[dst_port] = src_port
                return

        logger.debug(f"MapBidi: SrcPort: {src_port}, DstPort: {dst_port}")

        src_node, src_port = self._convert_port_address(src_port)
        dst_node, dst_port = self._convert_port_address(dst_port)

        if vlan_id is None:
            vlan_id = system_actions.get_available_vlan_id(
                self._vlan_min, self._vlan_max
            )
        else:
            vlan_id = system_actions.get_available_vlan_id(int(vlan_id), int(vlan_id))
        vle_name = f"{self._vle_prefix}{vlan_id}"

        system_actions.set_port_state(
            src_port,
            self._switch_mapping.get(src_node, "fabric")
            if self._switch_mapping
            else src_node,
            "enable",
        )
        system_actions.set_port_state(
            dst_port,
            self._switch_mapping.get(dst_node, "fabric")
            if self._switch_mapping
            else dst_node,
            "enable",
        )

        if src_node == dst_node:
            mapping_actions.map_bidi_single_node(
                node=src_node,
                src_port=src_port,
                dst_port=dst_port,
                vlan_id=vlan_id,
                vle_name=vle_name,
            )
        else:
            src_tunnel = self._tunnels_table.get((src_node, dst_node))
            dst_tunnel = self._tunnels_table.get((dst_node, src_node))
            if src_tunnel and dst_tunnel:
                mapping_actions.map_bidi_multi_node(
                    src_node=src_node,
                    dst_node=dst_node,
                    src_port=src_port,
                    dst_port=dst_port,
                    src_tunnel=src_tunnel,
                    dst_tunnel=dst_tunnel,
                    vlan_id=vlan_id,
                    vle_name=vle_name,
                )
            else:
                raise LayerOneDriverException("Cannot find the appropriate tunnel")

    def map_clear(self, ports: list[str]) -> None:
        """Remove simplex/duplex connection ending on the destination port."""
        logger.debug(f"MapClear: Ports: {', '.join(ports)}")

        # REST Implementation
        if self._rest_api_enabled and self._rest_api:
            self._remove_mapping(
                ports=ports,
                system_actions=RestSystemActions(api=self._rest_api),
                mapping_actions=RestMappingActions(
                    api=self._rest_api,
                    switch_mapping=self._switch_mapping,
                ),
            )

        # CLI Implementation
        else:
            with self._cli_handler.default_mode_service() as session:
                self._remove_mapping(
                    ports=ports,
                    system_actions=SystemActions(session),
                    mapping_actions=MappingActions(session),
                )

    def _remove_mapping(
        self,
        ports: list[str],
        system_actions: RestSystemActions | SystemActions,
        mapping_actions: RestMappingActions | MappingActions,
    ) -> None:
        exception_messages = []

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
                    mapping_actions.delete_single_node_vle(src_node, vle_name, vlan_id)
                else:
                    mapping_actions.delete_multi_node_vle(
                        src_node,
                        dst_node,
                        vle_name,
                        vlan_id,
                    )

                system_actions.set_port_state(
                    src_port,
                    self._switch_mapping.get(src_node, "fabric")
                    if self._switch_mapping
                    else src_node,
                    "disable",
                )
                system_actions.set_port_state(
                    dst_port,
                    self._switch_mapping.get(dst_node, "fabric")
                    if self._switch_mapping
                    else dst_node,
                    "disable",
                )

            except Exception as e:
                if len(e.args) > 1:
                    exception_messages.append(e.args[1])
                elif len(e.args) == 1:
                    exception_messages.append(e.args[0])
        if exception_messages:
            raise LayerOneDriverException(", ".join(exception_messages))

    def map_clear_to(self, src_port: str, dst_ports: list[str]) -> None:
        """Remove simplex/duplex connection ending on the destination port."""
        logger.debug(
            f"MapClearTo: SrcPort: {src_port}, DstPorts: {', '.join(dst_ports)}"
        )
        ports = [src_port]
        ports.extend(dst_ports)
        self.map_clear(ports)

    def map_tap(self, src_port: str, dst_ports: list[str]) -> None:
        raise LayerOneDriverException("MapTap is not supported")

    def get_attribute_value(
        self, cs_address: str, attribute_name: str
    ) -> AttributeValueResponseInfo:
        """Retrieve attribute value from the device."""
        if attribute_name == "Serial Number":
            if len(cs_address.split("/")) == 1:
                return AttributeValueResponseInfo(self._fabric_id)
            else:
                return AttributeValueResponseInfo("NA")
        else:
            raise LayerOneDriverException("GetAttributeValue command is not supported")

    def set_attribute_value(
        self, cs_address: str, attribute_name: str, attribute_value: int
    ) -> None:
        """Set attribute value to the device."""
        logger.debug(
            f"SetAttributeValue: "
            f"Addr: {cs_address}, Name: {attribute_name}, Value: {attribute_value}"
        )

        if attribute_name == "L1 VLAN ID" and self._map_on_set_vlan is True:
            vlan_id = attribute_value
            src_port = self._vlan_table.get(vlan_id)
            if src_port is None:
                logger.debug(f"Add vlan record {vlan_id}-{cs_address}")
                self._vlan_table[vlan_id] = cs_address
                return

            dst_port = cs_address
            req_dst_port = self._map_requests.get(src_port)
            req_src_port = self._map_requests.get(dst_port)
            logger.debug(
                f"Mapping called: "
                f"VlanID: {vlan_id}, SrcPort: {src_port}, DstPort: {dst_port}"
            )
            if all([req_src_port, req_dst_port]) and {req_src_port, req_dst_port} == {
                src_port,
                dst_port,
            }:
                self._map_requests.pop(src_port, None)
                self._map_requests.pop(dst_port, None)
                self._vlan_table.pop(vlan_id, None)
                return self.map_bidi(src_port, dst_port, int(vlan_id))

        raise LayerOneDriverException(
            f"SetAttributeValue for address {cs_address} is not supported."
        )

    def get_state_id(self) -> GetStateIdResponseInfo:
        """Check if CS synchronized with the device."""
        return GetStateIdResponseInfo(-1)

    def set_state_id(self, state_id: str) -> None:
        """Set synchronization state id to the device.

        Called after Autoload or SyncFomDevice commands.
        """
        pass

    def set_speed_manual(self, src_port: str, dst_port: str, speed: str, duplex: str):
        """Set connection speed.

        DEPRECATED. Is not used with the new standard
        """
        raise NotImplementedError

    def _valid_vlan_id(self, vlan_ids: list[int]) -> int:
        if vlan_ids:
            for vlan_id in vlan_ids:
                if self._vlan_min <= int(vlan_id) <= self._vlan_max:
                    return vlan_id
        raise LayerOneDriverException(
            f"Vlan ids {vlan_ids} is not correct or is not from allocated range"
        )

    @staticmethod
    def _convert_port_address(port: str) -> list[str]:
        """Convert CS port address."""
        return port.split("/")[1:3]
