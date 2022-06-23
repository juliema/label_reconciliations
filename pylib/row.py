from collections import UserDict


class Row(UserDict):
    def add_field(self, key, field):
        field.key = key
        self[key] = field
