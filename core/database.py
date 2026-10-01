"""
Модуль database.py — клас Database: управління набором таблиць,
збереження на диск і зчитування з диску (формат JSON).
"""

from __future__ import annotations
import json
import os

from .table import Table, Column, Row
from .types import create_type


class DatabaseError(ValueError):
    pass


class Database:
    def __init__(self, name: str = "database"):
        self.name = name
        self.tables: dict[str, Table] = {}

    # ---------- Управління таблицями ----------

    def create_table(self, name: str, columns: list[Column]) -> Table:
        if name in self.tables:
            raise DatabaseError(f"Таблиця '{name}' вже існує")
        if not columns:
            raise DatabaseError("Таблиця повинна мати хоча б одну колонку")
        table = Table(name, columns)
        self.tables[name] = table
        return table

    def drop_table(self, name: str):
        if name not in self.tables:
            raise DatabaseError(f"Таблиця '{name}' не знайдена")
        del self.tables[name]

    def get_table(self, name: str) -> Table:
        if name not in self.tables:
            raise DatabaseError(f"Таблиця '{name}' не знайдена")
        return self.tables[name]

    def list_tables(self) -> list[str]:
        return list(self.tables.keys())

    # ---------- Персистентність ----------

    def to_dict(self) -> dict:
        data = {"name": self.name, "tables": {}}
        for tname, table in self.tables.items():
            data["tables"][tname] = {
                "columns": [
                    {"name": c.name, "type": c.type.name} for c in table.columns
                ],
                "rows": [list(row.values) for row in table.rows],
            }
        return data

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Database":
        db = cls(name=data.get("name", "database"))
        for tname, tdata in data.get("tables", {}).items():
            columns = [
                Column(c["name"], create_type(c["type"])) for c in tdata["columns"]
            ]
            table = Table(tname, columns)
            for raw_row in tdata.get("rows", []):
                # значення інтервалів зберігаються як списки [min, max] -> кортеж
                values = []
                for col, val in zip(columns, raw_row):
                    if col.type.name == "realInvl" and isinstance(val, list):
                        values.append(tuple(val))
                    else:
                        values.append(val)
                table.rows.append(Row(values))
            db.tables[tname] = table
        return db

    @classmethod
    def load(cls, path: str) -> "Database":
        if not os.path.isfile(path):
            raise DatabaseError(f"Файл бази '{path}' не знайдено")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def __repr__(self):
        return f"Database({self.name}, tables={list(self.tables.keys())})"
