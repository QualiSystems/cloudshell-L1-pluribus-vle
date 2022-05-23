from cloudshell.cli.session.ssh_session import SSHSession


class VWSSHSession(SSHSession):
    def _connect_actions(self, prompt, logger):
        self.hardware_expect(
            command=None,
            expected_string=prompt,
            timeout=self._timeout,
            logger=logger
        )
        self.hardware_expect(
            command="pager off",
            expected_string=prompt,
            timeout=self._timeout,
            logger=logger
        )
