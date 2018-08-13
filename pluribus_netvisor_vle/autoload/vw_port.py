from cloudshell.layer_one.core.response.resource_info.entities.attributes import NumericAttribute
from cloudshell.layer_one.core.response.resource_info.entities.base import ResourceInfo
from cloudshell.layer_one.core.response.resource_info.entities.port import Port


class VWPort(Port):
    PROTOCOL_TYPE_VALUES = {
        '1g': '81',
        '10g': '82',
        '25g': '83',
        '40g': '84',
        '100g': '85'
    }

    def __init__(self, logical_id, phys_id):
        name = self.NAME_TEMPLATE.format(logical_id if len(str(logical_id)) > 1 else '0' + str(logical_id))
        ResourceInfo.__init__(self, phys_id, name, self.FAMILY_NAME, self.MODEL_NAME, 'NA')

    def set_protocol_type_by_speed(self, value):
        """
        :type value: str
        """
        num_value = self.PROTOCOL_TYPE_VALUES.get(value.lower())
        if num_value:
            self.attributes.append(NumericAttribute('Protocol Type', num_value))

    def set_protocol(self, value):
        """
        :type value: str
        """
        if value:
            self.attributes.append(NumericAttribute('Protocol', value))
