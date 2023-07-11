from dataclasses import dataclass
from typing import Any, Union
from pylib.flag import Flag

LIKE = """name field_set suffix task_id""".split()


@dataclass(kw_only=True)
class BaseField:
    name: str = ""
    note: str = ""
    flag: Flag = Flag.NO_FLAG
    field_set: str = ""  # All fields in this set get reconciled at the same time
    suffix: Union[int, float] = 0  # When columns have same name break the tie with this
    task_id: str = ""

    def to_dict(self, reconciled=False) -> dict[str, Any]:
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

    def header(self, attr: str = "") -> str:
        header = f"{self.field_name}: {attr}" if attr else self.field_name
        return header

    def decorate_dict(self, field_dict: dict[str, Any]) -> dict[str, Any]:
        field_dict[self.header("Explanation")] = self.note
        return field_dict

    @classmethod
    def like(cls, group, **kwargs):
        group = group if isinstance(group, list) else [group]
        field = group[0] if group else cls()
        new = field.copy_name(**kwargs)
        return new

    def copy_name(self, **kwargs):
        kwargs |= {k: self.__dict__[k] for k in LIKE}
        new = self.__class__(**kwargs)  # noqa
        return new
