from __future__ import annotations

from typing import TYPE_CHECKING

from cloudshell.cli.service.command_mode import CommandMode

if TYPE_CHECKING:
    from cloudshell.cli.service.cli_service import CliService


class ShellCommandMode(CommandMode):
    PROMPT = r".+\:.+\$\s*$"
    ENTER_COMMAND = "shell"
    EXIT_COMMAND = "exit"

    def __init__(self) -> None:
        CommandMode.__init__(
            self,
            self.PROMPT,
            self.ENTER_COMMAND,
            self.EXIT_COMMAND,
            enter_action_map=self.enter_action_map(),
            exit_action_map=self.exit_action_map(),
            enter_error_map=self.enter_error_map(),
            exit_error_map=self.exit_error_map(),
            use_exact_prompt=True,
        )

    def enter_actions(self, cli_operations: CliService) -> None:
        pass

    def enter_action_map(self) -> dict:
        return {}

    def enter_error_map(self) -> dict:
        return {r"[Ee]rror:": "Command error"}

    def exit_action_map(self) -> dict:
        return {}

    def exit_error_map(self) -> dict:
        return {r"[Ee]rror:": "Command error"}


class DefaultCommandMode(CommandMode):
    PROMPT = r"CLI\s+\(.+\)\s+>"
    ENTER_COMMAND = "cli"
    EXIT_COMMAND = "exit"

    def __init__(self):
        CommandMode.__init__(
            self,
            self.PROMPT,
            self.ENTER_COMMAND,
            self.EXIT_COMMAND,
            enter_action_map=self.enter_action_map(),
            exit_action_map=self.exit_action_map(),
            enter_error_map=self.enter_error_map(),
            exit_error_map=self.exit_error_map(),
            use_exact_prompt=True,
        )

    def enter_actions(self, cli_operations: CliService) -> None:
        pass

    def enter_action_map(self) -> dict:
        return {}

    def enter_error_map(self) -> dict:
        return {r"[Ee]rror:": "Command error"}

    def exit_action_map(self) -> dict:
        return {}

    def exit_error_map(self) -> dict:
        return {r"[Ee]rror:": "Command error"}


CommandMode.RELATIONS_DICT = {ShellCommandMode: {DefaultCommandMode: {}}}
