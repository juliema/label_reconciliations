from dataclasses import dataclass

from pylib.fields.base_field import BaseField


@dataclass(kw_only=True)
class NoOpField(BaseField):
    value: str = ""

    def to_dict(self):
        value = "" if self.is_reconciled else self.value
        return {self.label: value}

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        return cls()

    @staticmethod
    def results():
        return []
