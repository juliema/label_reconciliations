from collections import UserDict


class Row(UserDict):
    def add_field(self, key, field):
        field.key = key
        self[key] = field

    @staticmethod
    def all_keys(group):
        """Return a list of all keys in a possibly ragged group of rows.

        I'm hoping that the raggedness happens toward the end of rows.
        """
        keys = {}  # Dicts preserve order, sets do not
        for row in group:
            keys |= {k: 1 for k in row.keys()}
        return keys
