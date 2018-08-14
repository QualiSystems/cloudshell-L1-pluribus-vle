#!/usr/bin/python
# -*- coding: utf-8 -*-
from cloudshell.layer_one.core.response.resource_info.entities.attributes import StringAttribute
from cloudshell.layer_one.core.response.resource_info.entities.blade import Blade
from cloudshell.layer_one.core.response.resource_info.entities.validators import EntityValidator


class VLEBlade(Blade):
    """Blade resource entity"""
    NAME_TEMPLATE = 'Blade {}'
    FAMILY_NAME = 'L1 Switch Blade'
    MODEL_NAME = 'Generic L1 Module'

    def __init__(self, resource_id):
        super(VLEBlade, self).__init__(resource_id)
        self._model_name_attribute = None

    def set_model_name(self, value):
        self._model_name_attribute = value
        super(VLEBlade, self).set_model_name(value)

    def get_model_name(self):
        return self._model_name_attribute
