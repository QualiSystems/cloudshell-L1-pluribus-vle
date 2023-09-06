from __future__ import annotations

from cloudshell.layer_one.core.response.resource_info.entities.blade import Blade


class VLEBlade(Blade):
    """Blade resource entity."""

    NAME_TEMPLATE = "Node {}"
    FAMILY_NAME = "L1 Switch Blade"
    MODEL_NAME = "Generic L1 Module"

    def __init__(self, resource_id: str) -> None:
        super().__init__(resource_id)
        self._model_name_attribute: str | None = None

    def set_model_name(self, value: str | None) -> None:
        self._model_name_attribute = value
        super().set_model_name(value)

    def get_model_name(self) -> str | None:
        return self._model_name_attribute
