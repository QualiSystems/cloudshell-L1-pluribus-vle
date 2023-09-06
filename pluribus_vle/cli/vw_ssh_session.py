from __future__ import annotations

from cloudshell.cli.session.ssh_session import SSHSession


class VWSSHSession(SSHSession):
    def _connect_actions(self, prompt: str) -> None:
        self.hardware_expect(
            command=None,
            expected_string=prompt,
            timeout=self._timeout,
        )
        self.hardware_expect(
            command="pager off",
            expected_string=prompt,
            timeout=self._timeout,
        )
