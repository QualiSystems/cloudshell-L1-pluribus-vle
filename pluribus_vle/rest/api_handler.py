from __future__ import annotations

import ssl
from abc import abstractmethod

import requests
import urllib3


class PluribusApiException(Exception):  # noqa: N818
    """Base vSphere API Exception."""


class PluribusApiInvalidCredentials(PluribusApiException):
    def __init__(self):
        super().__init__("Connection failed. Please, check credentials.")


class PluribusApiInvalidRequest(PluribusApiException):
    def __init__(self):
        super().__init__("Invalid request values.")


class PluribusApiNonFound(PluribusApiException):
    def __init__(self):
        super().__init__("Data not found.")


class BaseAPIClient:
    def __init__(
        self,
        address: str,
        username: str,
        password: str,
        scheme: str = "http",
        port: int = 80,
        session: requests.Session = requests.Session(),
        verify_ssl=ssl.CERT_NONE,
    ) -> None:
        self.address = address
        self.username = username
        self.password = password
        self.session = session
        self.scheme = scheme
        self.port = port

        self.session.verify = verify_ssl
        if self.username and self.password:
            self.session.auth = (self.username, self.password)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @abstractmethod
    def _base_url(self):
        pass

    def _do_request(
        self,
        method,
        path: str,
        raise_for_status: bool = True,
        http_error_map: dict | None = None,
        **kwargs,
    ):
        if http_error_map is None:
            http_error_map = {}

        url = f"{self._base_url()}/{path}"
        result = method(url=url, **kwargs)
        try:
            raise_for_status and result.raise_for_status()
        except requests.exceptions.HTTPError as caught_err:
            http_code = caught_err.response.status_code
            err = http_error_map.get(http_code, PluribusApiException)
            raise err
        return result

    def _do_get(
        self,
        path: str,
        raise_for_status: bool = True,
        http_error_map: dict | None = None,
        **kwargs,
    ):
        """Basic GET request client method."""
        return self._do_request(
            self.session.get, path, raise_for_status, http_error_map, **kwargs
        )

    def _do_post(
        self, path: str, raise_for_status: bool = True, http_error_map=None, **kwargs
    ):
        """Basic POST request client method."""
        return self._do_request(
            self.session.post, path, raise_for_status, http_error_map, **kwargs
        )

    def _do_put(self, path, raise_for_status=True, http_error_map=None, **kwargs):
        """Basic PUT request client method."""
        return self._do_request(
            self.session.put, path, raise_for_status, http_error_map, **kwargs
        )

    def _do_delete(self, path, raise_for_status=True, http_error_map=None, **kwargs):
        """Basic DELETE request client method."""
        return self._do_request(
            self.session.delete, path, raise_for_status, http_error_map, **kwargs
        )


class PluribusRESTAPI(BaseAPIClient):
    ERROR_MAP = {
        401: PluribusApiInvalidCredentials,
        403: PluribusApiInvalidRequest,
        404: PluribusApiNonFound,
    }

    class Decorators:
        @classmethod
        def get_data(cls, decorated):
            def inner(*args, **kwargs):
                result = decorated(*args, **kwargs).json()
                if result.get("result", {}).get("status") == "Success":
                    return result.get("data", [])
                else:
                    raise PluribusApiException("Wrong response data.")

            return inner

        @classmethod
        def get_result_msg(cls, decorated):
            def inner(*args, **kwargs):
                result = decorated(*args, **kwargs).json()
                if result.get("result", {}).get("status") == "Success":
                    return result.get("result", {}).get("result")[0].get("message")
                else:
                    raise PluribusApiException("Wrong response data.")

            return inner

    def _base_url(self) -> str:
        return f"{self.scheme}://{self.address}:{self.port}/vRest"

    @Decorators.get_data
    def get_fabric_info(self) -> list:
        return self._do_get(path="fabrics/info", http_error_map=self.ERROR_MAP)

    @Decorators.get_data
    def get_switch_setup(self, fabric: bool = False) -> list:
        if fabric:
            path = "switch-setup?api.switch=fabric"
        else:
            path = "switch-setup"
        return self._do_get(path=path, http_error_map=self.ERROR_MAP)

    @Decorators.get_result_msg
    def set_state_id(self, state_id: str, fabric: bool = False) -> str:
        if fabric:
            path = "switch-setup?api.switch=fabric"
        else:
            path = "switch-setup"

        return self._do_put(
            path=path, json={"motd": state_id}, http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_switch_info(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"switch-info?api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_switch_software(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"software?api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_port_config(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"port-configs?api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_bezel_portmaps(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"bezel-portmaps?api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_port_associations(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"port-associations?api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_fabric_nodes(self, fabric_name: str) -> list:
        return self._do_get(
            path=f"fabric-nodes?fab-name={fabric_name}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_result_msg
    def create_vles(
        self,
        vle_name: str,
        node_1: str,
        node_2: str,
        node_1_port: str,
        node_2_port: str,
    ) -> str:
        return self._do_post(
            path="vles",
            json={
                "name": vle_name,
                "node-1": node_1,
                "node-2": node_2,
                "node-1-port": node_1_port,
                "node-2-port": node_2_port,
                "tracking": "true",
            },
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_data
    def get_vles(self) -> list:
        return self._do_get(path="vles", http_error_map=self.ERROR_MAP)

    @Decorators.get_data
    def get_vle_by_name(self, vle_name: str) -> list:
        return self._do_get(path=f"vles/{vle_name}", http_error_map=self.ERROR_MAP)

    def delete_vles(self, vle_name: str) -> None:
        self._do_delete(path=f"vles/{vle_name}", http_error_map=self.ERROR_MAP)

    @Decorators.get_result_msg
    def create_vlan(
        self, vlan_id: int, vxlan_id: int, port: str, hostid: int | str = "fabric"
    ) -> str:
        return self._do_post(
            path=f"vlans?api.switch={hostid}",
            json={
                "id": vlan_id,
                "scope": "local",
                "vxlan-mode": "transparent",
                "vxlan": vxlan_id,
                "ports": port,
            },
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_data
    def get_vlans(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"vlans?api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_vlan(self, vlan_id: int, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"vlans/id/{vlan_id}?api.switch={hostid}",
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_result_msg
    def delete_vlan(self, vlan_id: int, hostid: int | str = "fabric") -> str:
        return self._do_delete(
            path=f"vlans/id/{vlan_id}?api.switch={hostid}",
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_result_msg
    def add_ports_to_vlan(
        self, vlan_id: int, port: str, hostid: int | str = "fabric"
    ) -> str:
        return self._do_post(
            path=f"vlans/vlan-id/{vlan_id}/ports?api.switch={hostid}",
            json={"ports": port},
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_result_msg
    def delete_ports_from_vlan(
        self, vlan_id: int, ports: str, hostid: int | str = "fabric"
    ) -> str:
        return self._do_delete(
            path=f"vlans/vlan-id/{vlan_id}/ports/{ports}?api.switch={hostid}",
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_result_msg
    def add_vxlan_to_tunnel(
        self, tunnel_name: str, vxlan_id: int, hostid: int | str = "fabric"
    ) -> str:
        return self._do_post(
            path=f"tunnels/{tunnel_name}/vxlans?api.switch={hostid}",
            json={"vxlan": vxlan_id},
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_data
    def get_port_vlan_info(self, port: str, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"port-vlans?ports={port}&api.switch={hostid}",
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_data
    def get_port_status(self, port: str, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"ports?port={port}&api.switch={hostid}", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_data
    def get_tunnel_info(self, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"tunnels?auto-tunnel=false&api.switch={hostid}",
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_data
    def get_tunnel_vxlans(self, tunnel: str, hostid: int | str = "fabric") -> list:
        return self._do_get(
            path=f"tunnels/{tunnel}/vxlans?api.switch={hostid}",
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_data
    def get_phy_to_logical(self) -> list:
        return self._do_get(
            path="bezel-portmaps?api.switch=fabric", http_error_map=self.ERROR_MAP
        )

    @Decorators.get_result_msg
    def set_autoneg(
        self, port_id: str, hostid: int | str, is_autoneg: bool = True
    ) -> str:
        if is_autoneg:
            autoneg = "autoneg"
        else:
            autoneg = "no-autoneg"

        return self._do_put(
            path=f"port-configs/{port_id}?api.switch={hostid}",
            json={"autoneg": autoneg},
            http_error_map=self.ERROR_MAP,
        )

    @Decorators.get_result_msg
    def set_port_state(
        self, port_id: str, hostid: int | str, port_state: str = "enable"
    ) -> str:
        return self._do_put(
            path=f"port-configs/{port_id}?api.switch={hostid}",
            json={"enable": port_state},
            http_error_map=self.ERROR_MAP,
        )
