"""
Модуль table.py — Column, Row, Table.
"""

from __future__ import annotations
from .types import FieldType, FieldTypeError


class Column:
    def __init__(self, name: str, field_type: FieldType):
        self.name = name
        self.type = field_type

    def __repr__(self):
        return f"Column({self.name}: {self.type.name})"

    def __eq__(self, other):
        return (
            isinstance(other, Column)
            and self.name == other.name
            and self.type.name == other.type.name
        )


class Row:
    def __init__(self, values: list):
        # values — список уже РОЗПАРСЕНИХ значень (у внутрішньому форматі типів)
        self.values = list(values)

    def __repr__(self):
        return f"Row({self.values})"

    def __eq__(self, other):
        return isinstance(other, Row) and self.values == other.values

    def __hash__(self):
        return hash(tuple(self.values))


class TableError(ValueError):
    pass


class Table:
    def __init__(self, name: str, columns: list[Column] | None = None):
        self.name = name
        self.columns: list[Column] = columns or []
        self.rows: list[Row] = []

    # ---------- Схема ----------

    def add_column(self, column: Column):
        if any(c.name == column.name for c in self.columns):
            raise TableError(f"Колонка '{column.name}' вже існує")
        self.columns.append(column)

    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def has_same_schema(self, other: "Table") -> bool:
        return self.columns == other.columns

    # ---------- Валідація ----------

    def validate_row(self, raw_values: list) -> bool:
        if len(raw_values) != len(self.columns):
            return False
        return all(
            col.type.validate(raw) for col, raw in zip(self.columns, raw_values)
        )

    # ---------- CRUD рядків ----------

    def add_row(self, raw_values: list) -> Row:
        if len(raw_values) != len(self.columns):
            raise TableError(
                f"Очікувалось {len(self.columns)} значень, отримано {len(raw_values)}"
            )
        parsed = []
        for col, raw in zip(self.columns, raw_values):
            if not col.type.validate(raw):
                raise FieldTypeError(
                    f"Некоректне значення '{raw}' для колонки '{col.name}' ({col.type.name})"
                )
            parsed.append(col.type.parse(raw))
        row = Row(parsed)
        self.rows.append(row)
        return row

    def edit_row(self, index: int, raw_values: list) -> Row:
        if not (0 <= index < len(self.rows)):
            raise TableError(f"Немає рядка з індексом {index}")
        if len(raw_values) != len(self.columns):
            raise TableError(
                f"Очікувалось {len(self.columns)} значень, отримано {len(raw_values)}"
            )
        parsed = []
        for col, raw in zip(self.columns, raw_values):
            if not col.type.validate(raw):
                raise FieldTypeError(
                    f"Некоректне значення '{raw}' для колонки '{col.name}' ({col.type.name})"
                )
            parsed.append(col.type.parse(raw))
        self.rows[index] = Row(parsed)
        return self.rows[index]

    def delete_row(self, index: int):
        if not (0 <= index < len(self.rows)):
            raise TableError(f"Немає рядка з індексом {index}")
        del self.rows[index]

    def get_rows(self) -> list[Row]:
        return self.rows

    def get_rows_as_strings(self) -> list[list[str]]:
        """Рядки у вигляді рядкових значень — зручно для показу в GUI (Treeview)."""
        result = []
        for row in self.rows:
            result.append(
                [
                    col.type.to_string(val)
                    for col, val in zip(self.columns, row.values)
                ]
            )
        return result

    def __repr__(self):
        return f"Table({self.name}, columns={self.columns}, rows={len(self.rows)})"
