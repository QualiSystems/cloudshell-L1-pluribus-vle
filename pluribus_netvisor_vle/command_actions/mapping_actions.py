import re
from copy import copy

import pluribus_netvisor_vle.command_templates.mapping as command_template
from cloudshell.cli.command_template.command_template_executor import CommandTemplateExecutor


class MappingActions(object):
    PORTS = 'ports'
    BIDIR = 'bidir'
    MONITOR_PORTS = 'monitor_ports'

    """
    Autoload actions
    """

    def __init__(self, cli_service, logger):
        """
        :param logger:
        :type logger: Logger
        :return:
        """
        self._logger = logger
        self._cli_service = cli_service

        self.__associations_table = None
        self.__phys_to_logical_table = None

    @property
    def cli_service(self):
        return self._cli_service

    @cli_service.setter
    def cli_service(self, cli_service):
        self._cli_service = cli_service

    @staticmethod
    def _parse_complex_ports(port_string):
        ports = []
        for port in port_string.split(','):
            if '-' in port:
                start, end = port.split('-')
                ports.extend(map(str, range(int(start), int(end) + 1)))
            elif port:
                ports.append(port)
        return ports

    def _build_associations_table(self):
        associations_table = {}
        output = CommandTemplateExecutor(self._cli_service, command_template.ASSOCIATIONS).execute_command()
        for master_port, slave_port, name, bidir, monitor_ports in re.findall(r'^(\d+):(\d+):([\w-]+):(\w+):([\d,-]*)$',
                                                                              output, flags=re.MULTILINE):
            associations_table[name] = {self.PORTS: [master_port, slave_port],
                                        self.BIDIR: bidir.lower() == 'true',
                                        self.MONITOR_PORTS: self._parse_complex_ports(monitor_ports)}
        return associations_table

    @property
    def _associations_table(self):
        if not self.__associations_table:
            self.__associations_table = self._build_associations_table()
        return self.__associations_table

    def _build_phys_to_logical_table(self):
        logical_to_phys_dict = {}
        output = CommandTemplateExecutor(self._cli_service, command_template.PHYS_TO_LOGICAL).execute_command()
        for phys_id, logical_id in re.findall(r'^([\d.]+):(\d+)$', output, flags=re.MULTILINE):
            logical_to_phys_dict[phys_id] = logical_id
        return logical_to_phys_dict

    @property
    def _phys_to_logical_table(self):
        if not self.__phys_to_logical_table:
            self.__phys_to_logical_table = self._build_phys_to_logical_table()
        return self.__phys_to_logical_table

    def _get_logical(self, phys_name):
        logical_id = self._phys_to_logical_table.get(phys_name)
        if logical_id:
            return logical_id
        else:
            raise Exception(self.__class__.__name__, 'Cannot convert physical port name to logical')

    def _find_association(self, port):
        for name, attributes in self._associations_table.iteritems():
            if port in attributes.get(self.PORTS):
                return name

    # def _find_unidir_association(self, ports):
    #     for name, attributes in self._associations_table.iteritems():
    #         if ports == attributes.get(self.PORTS) and not attributes.get(self.BIDIR):
    #             return name
    # def _find_monitor_association(self, port):
    #     for name, attributes in self._associations_table.iteritems():

    def map_uni(self, master_port, slave_ports):
        logical_master_id = self._get_logical(master_port)
        self._validate_port(logical_master_id)
        command_executor = CommandTemplateExecutor(self._cli_service, command_template.MAP_UNI)
        exception_messages = []
        for slave_port in slave_ports:
            try:
                logical_slave_id = self._get_logical(slave_port)
                self._validate_port(logical_slave_id)
                command_executor.execute_command(master_ports=logical_master_id, slave_ports=logical_slave_id,
                                                 name='{0}-uni-{1}'.format(logical_master_id, logical_slave_id))
            except Exception as e:
                if len(e.args) > 1:
                    exception_messages.append(e.args[1])
                elif len(e.args) == 1:
                    exception_messages.append(e.args[0])
        if exception_messages:
            raise Exception(self.__class__.__name__, ', '.join(exception_messages))

    def map_bidi(self, master_port, slave_port):
        logical_master_id = self._get_logical(master_port)
        self._validate_port(logical_master_id)
        logical_slave_id = self._get_logical(slave_port)
        self._validate_port(logical_slave_id)
        associations_output = CommandTemplateExecutor(self._cli_service, command_template.MAP_BIDI).execute_command(
            master_ports=logical_master_id, slave_ports=logical_slave_id,
            name='{0}-bidi-{1}'.format(logical_master_id, logical_slave_id))
        return associations_output

    def map_clear(self, ports):
        exception_messages = []
        for port in ports:
            try:
                port_id = self._get_logical(port)
                association = self._find_association(port_id)
                self._remove_association(association)
            except Exception as e:
                if len(e.args) > 1:
                    exception_messages.append(e.args[1])
                elif len(e.args) == 1:
                    exception_messages.append(e.args[0])
        if exception_messages:
            raise Exception(self.__class__.__name__, ', '.join(exception_messages))

    def _remove_association(self, association_name):
        if association_name:
            command_executor = CommandTemplateExecutor(self._cli_service, command_template.MAP_CLEAR)
            command_executor.execute_command(name=association_name)
            del self._associations_table[association_name]

    def _modify_monitor_ports(self, association_name, monitor_ports):
        association_attributes = self._associations_table.get(association_name)
        if association_attributes.get(self.MONITOR_PORTS) != monitor_ports:
            command_executor = CommandTemplateExecutor(self._cli_service, command_template.MODIFY_MONITOR_PORTS)
            command_executor.execute_command(name=association_name, ports=','.join(monitor_ports))
            association_attributes[self.MONITOR_PORTS] = monitor_ports

    def map_clear_to(self, master_port, slave_ports):
        master_port_logical_id = self._get_logical(master_port)
        slave_ports_logical_ids = map(self._get_logical, slave_ports)
        exception_messages = []
        try:
            association_name = self._find_association(master_port_logical_id)
            if association_name:
                association_attributes = self._associations_table.get(association_name)
                association_ports = association_attributes.get(self.PORTS)
                # Second port of association
                association_second_port = association_ports[1 - association_ports.index(master_port_logical_id)]
                if association_second_port in slave_ports_logical_ids:
                    self._remove_association(association_name)
                else:
                    monitor_ports = copy(association_attributes.get(self.MONITOR_PORTS))
                    for port in slave_ports_logical_ids:
                        if port in monitor_ports:
                            monitor_ports.remove(port)
                    self._modify_monitor_ports(association_name, monitor_ports)

        except Exception as e:
            if len(e.args) > 1:
                exception_messages.append(e.args[1])
            elif len(e.args) == 1:
                exception_messages.append(e.args[0])
        if exception_messages:
            raise Exception(self.__class__.__name__, ', '.join(exception_messages))

    def map_tap(self, master_port, monitor_ports):
        master_port_logical = self._get_logical(master_port)
        self._validate_port(master_port_logical)
        monitor_ports_logical = map(self._get_logical, monitor_ports)
        association_name = self._find_association(master_port_logical)
        if not association_name:
            raise Exception(self.__class__.__name__,
                            "Cannot find association with port {}".format(master_port_logical))
        association_attributes = self._associations_table.get(association_name)
        association_monitor_ports = copy(association_attributes.get(self.MONITOR_PORTS))
        for port in monitor_ports_logical:
            self._validate_port(port)
            if port in association_monitor_ports:
                raise Exception(self.__class__.__name__,
                                'Port {0} has already exist in monitor ports for association {1}'.format(port,
                                                                                                         association_name))
            else:
                association_monitor_ports.append(port)
        self._modify_monitor_ports(association_name, association_monitor_ports)

    def _validate_port(self, logical_port_id):
        output = CommandTemplateExecutor(self._cli_service, command_template.IS_ENABLED).execute_command(
            port=logical_port_id)
        if '{}:on'.format(logical_port_id) in output.lower():
            return
        raise Exception('Port {} is disabled'.format(logical_port_id))
