#!/usr/bin/python
# -*- coding: utf-8 -*-
from collections import OrderedDict

from cloudshell.cli.command_mode import CommandMode


class ShellCommandMode(CommandMode):
    PROMPT = r".+\:.+\$\s*$"
    ENTER_COMMAND = "shell"
    EXIT_COMMAND = "exit"

    def __init__(self):
        CommandMode.__init__(self, self.PROMPT, self.ENTER_COMMAND, self.EXIT_COMMAND,
                             enter_action_map=self.enter_action_map(),
                             exit_action_map=self.exit_action_map(),
                             enter_error_map=self.enter_error_map(),
                             exit_error_map=self.exit_error_map(),
                             use_exact_prompt=True)

    def enter_actions(self, cli_operations):
        pass

    def enter_action_map(self):
        return OrderedDict()

    def enter_error_map(self):
        return OrderedDict([(r"[Ee]rror:", "Command error")])

    def exit_action_map(self):
        return OrderedDict()

    def exit_error_map(self):
        return OrderedDict([(r"[Ee]rror:", "Command error")])


class DefaultCommandMode(CommandMode):
    PROMPT = r"CLI\s+\(.+\)\s+>"
    ENTER_COMMAND = "cli"
    EXIT_COMMAND = "exit"

    def __init__(self):
        CommandMode.__init__(self, self.PROMPT, self.ENTER_COMMAND, self.EXIT_COMMAND,
                             enter_action_map=self.enter_action_map(),
                             exit_action_map=self.exit_action_map(),
                             enter_error_map=self.enter_error_map(),
                             exit_error_map=self.exit_error_map(),
                             use_exact_prompt=True)

    def enter_actions(self, cli_operations):
        pass

    def enter_action_map(self):
        return OrderedDict()

    def enter_error_map(self):
        return OrderedDict([(r"[Ee]rror:", "Command error")])

    def exit_action_map(self):
        return OrderedDict()

    def exit_error_map(self):
        return OrderedDict([(r"[Ee]rror:", "Command error")])


CommandMode.RELATIONS_DICT = {
    ShellCommandMode: {
        DefaultCommandMode: {
        }
    }
}
