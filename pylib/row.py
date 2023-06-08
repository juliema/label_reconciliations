import dataclasses
from typing import Any


@dataclasses.dataclass
class Row:
    fields: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __getitem__(self, key):
        return self.fields[key]

    def __contains__(self, key):
        return key in self.fields

    def add_field(self, name, field, task_id: str = ""):
        name = self.rename(name.strip(), task_id)
        field.name = name
        self.fields[name] = field

    def values(self):
        return self.fields.values()

    def rename(self, name: str, task_id: str) -> str:
        tie = 1
        new_name = f"{task_id}_{tie} {name}" if task_id else name
        while new_name in self.fields:
            tie += 1
            new_name = f"{task_id}_{tie} {name}" if task_id else f"{name} {tie}"
        return new_name
