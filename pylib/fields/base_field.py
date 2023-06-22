from dataclasses import dataclass, replace
from typing import Any, Union
from pylib.flag import Flag


@dataclass(kw_only=True)
class BaseField:
    name: str = ""
    note: str = ""
    flag: Flag = Flag.NO_FLAG
    field_set: str = ""  # All fields in this set get reconciled at the same time
    suffix: Union[int, float] = 0  # When columns have same name break the tie with this
    task_id: str = ""

    def to_dict(self, reconciled=False, add_note=False) -> dict[str, Any]:
        raise NotImplementedError()

    @classmethod
    def reconcile(cls, group, row_count, args=None):
        raise NotImplementedError()

    @property
    def name_group(self) -> str:
        return f"{self.task_id}_{self.name}" if self.task_id else self.name

    @property
    def field_name(self) -> str:
        return f"{self.name_group}_{self.suffix}" if self.suffix else self.name_group

    def header(self, attr: str) -> str:
        return f"{self.field_name}: {attr}"

    def decorate_dict(
        self, field_dict: dict[str, Any], add_note=False
    ) -> dict[str, Any]:
        if add_note:
            field_dict[self.header("Explanation")] = self.note
        return field_dict

    @classmethod
    def copy(cls, group, **kwargs):
        src = group[0] if group else cls()
        dst = replace(src, **kwargs)
        return dst
