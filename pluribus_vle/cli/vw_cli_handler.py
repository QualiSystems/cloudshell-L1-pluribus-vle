#!/usr/bin/python
# -*- coding: utf-8 -*-

from cloudshell.cli.cli import CLI
from cloudshell.cli.command_mode_helper import CommandModeHelper
from cloudshell.cli.session.telnet_session import TelnetSession
from cloudshell.cli.session_pool_manager import SessionPoolManager
from cloudshell.layer_one.core.helper.runtime_configuration import RuntimeConfiguration
from cloudshell.layer_one.core.layer_one_driver_exception import LayerOneDriverException
from pluribus_vle.cli.command_modes import DefaultCommandMode
from pluribus_vle.cli.vw_ssh_session import VWSSHSession


class VWCliHandler(object):
    def __init__(self, logger):
        self._logger = logger
        self._cli = CLI(session_pool=SessionPoolManager(max_pool_size=1))
        self.modes = CommandModeHelper.create_command_mode()
        self._defined_session_types = {'SSH': VWSSHSession, 'TELNET': TelnetSession}

        self._session_types = RuntimeConfiguration().read_key(
            'CLI.TYPE', ['SSH']) or self._defined_session_types.keys()
        self._ports = RuntimeConfiguration().read_key('CLI.PORTS', '22')

        self._host = None
        self._username = None
        self._password = None

    def _new_sessions(self):
        sessions = []
        for session_type in self._session_types:
            session_class = self._defined_session_types.get(session_type)
            if not session_class:
                raise LayerOneDriverException(self.__class__.__name__,
                                              'Session type {} is not defined'.format(session_type))
            port = self._ports.get(session_type)
            sessions.append(session_class(self._host, self._username, self._password, port))
        return sessions

    def define_session_attributes(self, address, username, password):
        """
        Define session attributes
        :param address: 
        :type address: str
        :param username: 
        :param password: 
        :return: 
        """

        address_list = address.split(':')
        if len(address_list) > 1:
            raise LayerOneDriverException(self.__class__.__name__, 'Incorrect resource address')
        self._host = address
        self._username = username
        self._password = password

    def get_cli_service(self, command_mode):
        """
        Create new cli service or get it from pool
        :param command_mode: 
        :return: 
        """
        if not self._host or not self._username or not self._password:
            raise LayerOneDriverException(self.__class__.__name__,
                                          "Cli Attributes is not defined, call Login command first")
        return self._cli.get_session(self._new_sessions(), command_mode, self._logger)

    @property
    def _default_mode(self):
        return self.modes[DefaultCommandMode]

    def default_mode_service(self):
        """
        Default mode session
        :return:
        :rtype: cloudshell.cli.cli_service.CliService
        """
        return self.get_cli_service(self._default_mode)
