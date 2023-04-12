class RestAutoloadActions(object):
    """ Autoload actions. """

    def __init__(self, api, switch_mapping, logger):
        self._api = api
        self._switch_mapping = switch_mapping
        self._logger = logger

    def ports_table(self, switch_name):
        """ Get ports table. """
        port_table = {}
        data = self._api.get_port_config(
            hostid=self._switch_mapping.get(switch_name, "fabric")
        )

        for port in data:
            port_table[port["port"]] = {
                "speed": str(port.get("speed", "")),
                "autoneg": port.get("autoneg")
            }

        return port_table

    def associations_table(self):
        """ Get node-port associations table. """
        data = self._api.get_vles()
        associations_table = {}

        for vle in data:
            master_port = (vle["node1-name"], str(vle["node-1-port"]))
            slave_port = (vle["node2-name"], str(vle["node-2-port"]))
            associations_table.update(
                {
                    master_port: slave_port,
                    slave_port: master_port
                }
            )
        return associations_table

    def fabric_nodes_table(self, fabric_name):
        """ Get fabric nodes data. """
        data = self._api.get_fabric_nodes(fabric_name=fabric_name)

        nodes_table = {}

        for node in data:
            node_name = node["name"]
            node_id = node["id"]
            nodes_table[node_name] = self._switch_info_table(node_id)

        return nodes_table

    def _switch_info_table(self, switch_id):
        """ Get switch info. """
        data = self._api.get_switch_info(hostid=switch_id)[0]

        return {"model": data.get("model", "Undefined"),
                "chassis-serial": data.get("chassis-serial", "Undefined")}
