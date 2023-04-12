import ssl
from abc import abstractmethod

import requests
import urllib3


class PluribusApiException(Exception):
    """Base vSphere API Exception."""


class PluribusApiInvalidCredentials(PluribusApiException):
    def __init__(self):
        super(PluribusApiInvalidCredentials, self).__init__(
            "Connection failed. Please, check credentials."
        )


class PluribusApiInvalidRequest(PluribusApiException):
    def __init__(self):
        super(PluribusApiInvalidRequest, self).__init__(
            "Invalid request values."
        )


class PluribusApiNonFound(PluribusApiException):
    def __init__(self):
        super(PluribusApiNonFound, self).__init__(
            "Data not found."
        )


class BaseAPIClient:
    def __init__(
            self,
            address,
            username,
            password,
            scheme="http",
            port=80,
            session=requests.Session(),
            verify_ssl=ssl.CERT_NONE
    ):
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
        path,
        raise_for_status=True,
        http_error_map=None,
        **kwargs
    ):
        if http_error_map is None:
            http_error_map = {}

        url = "{base_url}/{path}".format(base_url=self._base_url(), path=path)
        result = method(url=url, **kwargs)
        try:
            raise_for_status and result.raise_for_status()
        except requests.exceptions.HTTPError as caught_err:
            http_code = caught_err.response.status_code
            err = http_error_map.get(http_code, PluribusApiException)
            raise err
        return result

    def _do_get(self, path, raise_for_status=True, http_error_map=None, **kwargs):
        """Basic GET request client method."""
        return self._do_request(
            self.session.get, path, raise_for_status, http_error_map, **kwargs
        )

    def _do_post(self, path, raise_for_status=True, http_error_map=None, **kwargs):
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
        404: PluribusApiNonFound
        }

    class Decorators:
        @classmethod
        def get_data(cls, decorated):
            def inner(*args, **kwargs):
                result = decorated(*args, **kwargs).json()
                if result.get("result", dict()).get("status") == "Success":
                    return result.get("data", [])
                else:
                    raise PluribusApiException("Wrong response data.")
            return inner

        @classmethod
        def get_result_msg(cls, decorated):
            def inner(*args, **kwargs):
                result = decorated(*args, **kwargs).json()
                if result.get("result", dict()).get("status") == "Success":
                    return result.get("result", dict()).get("result")[0].get("message")
                else:
                    raise PluribusApiException("Wrong response data.")
            return inner

    def _base_url(self):
        return "{scheme}://{address}:{port}/vRest".format(
            scheme=self.scheme,
            address=self.address,
            port=self.port
        )

    @Decorators.get_data
    def get_fabric_info(self):
        return self._do_get(
            path="fabrics/info",
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_switch_setup(self, fabric=False):
        if fabric:
            path = "switch-setup?api.switch=fabric"
        else:
            path = "switch-setup"
        return self._do_get(
            path=path,
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def set_state_id(self, state_id, fabric=False):
        if fabric:
            path = "switch-setup?api.switch=fabric"
        else:
            path = "switch-setup"

        return self._do_put(
            path=path,
            json={"motd": state_id},
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_switch_info(self, hostid="fabric"):

        return self._do_get(
            path="switch-info?api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_switch_software(self, hostid="fabric"):

        return self._do_get(
            path="software?api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_port_config(self, hostid="fabric"):

        return self._do_get(
            path="port-configs?api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_bezel_portmaps(self, hostid="fabric"):

        return self._do_get(
            path="bezel-portmaps?api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_port_associations(self, hostid="fabric"):

        return self._do_get(
            path="port-associations?api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_fabric_nodes(self, fabric_name):

        return self._do_get(
            path="fabric-nodes?fab-name={fabric_name}".format(fabric_name=fabric_name),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def create_vles(self, vle_name, node_1, node_2, node_1_port, node_2_port):

        return self._do_post(
            path="vles",
            json={"name": vle_name,
                  "node-1": node_1,
                  "node-2": node_2,
                  "node-1-port": node_1_port,
                  "node-2-port": node_2_port,
                  "tracking": "true"
                  },
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_vles(self):

        return self._do_get(
            path="vles",
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_vle_by_name(self, vle_name):

        return self._do_get(
            path="vles/{vle_name}".format(vle_name=vle_name),
            http_error_map=self.ERROR_MAP
            )

    def delete_vles(self, vle_name):

        return self._do_delete(
            path="vles/{vle_name}".format(vle_name=vle_name),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def create_vlan(self, vlan_id, vxlan_id, port, hostid="fabric"):

        return self._do_post(
            path="vlans?api.switch={hostid}".format(hostid=hostid),
            json={"id": vlan_id,
                  "scope": "local",
                  "vxlan-mode": "transparent",
                  "vxlan": vxlan_id,
                  "ports": port},
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_vlans(self, hostid="fabric"):

        return self._do_get(
            path="vlans?api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_vlan(self, vlan_id, hostid="fabric"):

        return self._do_get(
            path="vlans/id/{vlan_id}?api.switch={hostid}".format(vlan_id=vlan_id,
                                                                 hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def delete_vlan(self, vlan_id, hostid="fabric"):

        return self._do_delete(
            path="vlans/id/{vlan_id}?api.switch={hostid}".format(vlan_id=vlan_id,
                                                                 hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def add_ports_to_vlan(self, vlan_id, port, hostid="fabric"):

        return self._do_post(
            path="vlans/vlan-id/{vlan_id}/ports?api.switch={hostid}".format(
                vlan_id=vlan_id,
                hostid=hostid
            ),
            json={"ports": port},
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def delete_ports_from_vlan(self, vlan_id, ports, hostid="fabric"):

        return self._do_delete(
            path="vlans/vlan-id/{vlan_id}/ports/{ports}?api.switch={hostid}".format(
                vlan_id=vlan_id,
                hostid=hostid,
                ports=ports
            ),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def add_vxlan_to_tunnel(self, tunnel_name, vxlan_id, hostid="fabric"):

        return self._do_post(
            path="tunnels/{tunnel_name}/vxlans?api.switch={hostid}".format(
                tunnel_name=tunnel_name,
                hostid=hostid
            ),
            json={"vxlan": vxlan_id},
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_port_vlan_info(self, port, hostid="fabric"):

        return self._do_get(
            path="port-vlans?ports={port}&api.switch={hostid}".format(
                port=port,
                hostid=hostid
            ),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_port_status(self, port, hostid="fabric"):

        return self._do_get(
            path="ports?port={port}&api.switch={hostid}".format(
                port=port,
                hostid=hostid
            ),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_tunnel_info(self, hostid="fabric"):

        return self._do_get(
            path="tunnels?auto-tunnel=false&api.switch={hostid}".format(hostid=hostid),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_tunnel_vxlans(self, tunnel, hostid="fabric"):

        return self._do_get(
            path="tunnels/{tunnel}/vxlans?api.switch={hostid}".format(
                tunnel=tunnel,
                hostid=hostid
            ),
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_data
    def get_phy_to_logical(self):

        return self._do_get(
            path="bezel-portmaps?api.switch=fabric",
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def set_autoneg(self, port_id, hostid, is_autoneg=True):

        if is_autoneg:
            autoneg = "autoneg"
        else:
            autoneg = "no-autoneg"

        return self._do_put(
            path="port-configs/{port_id}?api.switch={hostid}".format(
                port_id=port_id,
                hostid=hostid
            ),
            json={"autoneg": autoneg},
            http_error_map=self.ERROR_MAP
            )

    @Decorators.get_result_msg
    def set_port_state(self, port_id, hostid, port_state="enable"):

        return self._do_put(
            path="port-configs/{port_id}?api.switch={hostid}".format(
                port_id=port_id,
                hostid=hostid
            ),
            json={"enable": port_state},
            http_error_map=self.ERROR_MAP
            )
