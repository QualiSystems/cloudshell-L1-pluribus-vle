from cloudshell.layer_one.core.response.resource_info.entities.attributes import StringAttribute
from cloudshell.layer_one.core.response.resource_info.entities.base import ResourceInfo


class VLEFabric(ResourceInfo):
    """
    Chassis resource entity
    """
    NAME_TEMPLATE = 'Fabric {}'
    FAMILY_NAME = 'L1 Switch'
    MODEL_NAME = 'Pluribus Netvisor VLE Fabric'

    def __init__(self, resource_id, address, serial_number=None):
        self._address = address
        name = self.NAME_TEMPLATE.format(resource_id)
        family_name = self.FAMILY_NAME
        serial_number = serial_number or 'NA'
        super(VLEFabric, self).__init__(resource_id, name, family_name, self.MODEL_NAME, serial_number)

    @property
    def address(self):
        return self._address

    def set_fabric_name(self, value):
        if value:
            self.attributes.append(StringAttribute('Fabric Name', value))

    def set_serial_number(self, value):
        if value:
            self.attributes.append(StringAttribute('Serial Number', value))
