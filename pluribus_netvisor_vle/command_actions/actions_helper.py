import re


class ActionsManager(object):
    def __init__(self, actions_instance, cli_service):
        self._actions_instance = actions_instance
        self._cli_service = cli_service

    def __enter__(self):
        self._actions_instance.cli_service = self._cli_service
        return self._actions_instance

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._actions_instance.cli_service = None


class ActionsHelper(object):
    @staticmethod
    def parse_table(out):
        table = {}
        for line in out.splitlines():
            match = re.match(r'\s*(.+):(.+)\s*', line)
            if match:
                table[match.group(1).strip()] = match.group(2).strip()
        return table
