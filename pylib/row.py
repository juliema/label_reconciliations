import dataclasses
from collections import defaultdict
from typing import Any


@dataclasses.dataclass
class Row:
    fields: dict[str, Any] = dataclasses.field(default_factory=dict)

    _names: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=lambda: defaultdict(int)
    )

    def add_field(self, name, field, task_id: str = ""):
        if task_id:
            self._names[(task_id, name)] += 1
            name = f"{task_id}_{self._names[(task_id, name)]} {name}"
        field.name = name
        self.fields[name] = field
