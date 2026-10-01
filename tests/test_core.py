"""
Unit-тести для ядра міні-СУБД.

Запуск: pytest -v  (з кореневої директорії проєкту minidb/)

Тести:
  1. test_realinvl_validation      — валідація типу realInvl (базові типи + додатковий тип)
  2. test_database_save_load_roundtrip — збереження/зчитування бази з диску
  3. test_intersect_basic          — ІНДИВІДУАЛЬНА ОПЕРАЦІЯ ВАРІАНТУ: перетин таблиць
  4. test_intersect_schema_mismatch_raises — перетин таблиць з різною схемою -> помилка
  5. test_table_row_validation     — валідація рядка не дозволяє додати некоректні дані
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.types import (
    IntegerType,
    RealType,
    StringType,
    RealIntervalType,
    FieldTypeError,
)
from core.table import Column, Table, TableError
from core.database import Database
from core.operations import intersect


# ---------------------------------------------------------------------------
# 1. Валідація типу realInvl (додатковий тип за варіантом)
# ---------------------------------------------------------------------------
def test_realinvl_validation():
    t = RealIntervalType()

    assert t.validate("1.5;3.2") is True
    assert t.parse("1.5;3.2") == (1.5, 3.2)

    # некоректний інтервал: min > max
    assert t.validate("5.0;2.0") is False
    with pytest.raises(FieldTypeError):
        t.parse("5.0;2.0")

    # некоректний формат
    assert t.validate("not-an-interval") is False


# ---------------------------------------------------------------------------
# 2. Збереження і зчитування бази з диску (round-trip)
# ---------------------------------------------------------------------------
def test_database_save_load_roundtrip():
    db = Database("test_db")
    table = db.create_table(
        "students",
        [
            Column("id", IntegerType()),
            Column("name", StringType()),
            Column("score", RealType()),
        ],
    )
    table.add_row(["1", "Ivan", "4.5"])
    table.add_row(["2", "Olena", "5.0"])

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "db.json")
        db.save(path)
        assert os.path.isfile(path)

        loaded = Database.load(path)
        loaded_table = loaded.get_table("students")

        assert loaded_table.column_names() == ["id", "name", "score"]
        assert len(loaded_table.rows) == 2
        assert loaded_table.rows[0].values == [1, "Ivan", 4.5]
        assert loaded_table.rows[1].values == [2, "Olena", 5.0]


# ---------------------------------------------------------------------------
# 3. ІНДИВІДУАЛЬНА ОПЕРАЦІЯ ВАРІАНТУ: перетин таблиць
# ---------------------------------------------------------------------------
def test_intersect_basic():
    cols = [Column("id", IntegerType()), Column("name", StringType())]

    t1 = Table("t1", cols)
    t1.add_row(["1", "Ivan"])
    t1.add_row(["2", "Olena"])
    t1.add_row(["3", "Petro"])

    t2 = Table("t2", [Column("id", IntegerType()), Column("name", StringType())])
    t2.add_row(["2", "Olena"])
    t2.add_row(["3", "Petro"])
    t2.add_row(["4", "Maria"])

    result = intersect(t1, t2)

    result_values = sorted([row.values for row in result.rows], key=lambda v: v[0])
    assert result_values == [[2, "Olena"], [3, "Petro"]]
    # результат не повинен містити рядки, яких немає в обох таблицях
    assert [1, "Ivan"] not in result_values
    assert [4, "Maria"] not in result_values


def test_intersect_schema_mismatch_raises():
    t1 = Table("t1", [Column("id", IntegerType())])
    t2 = Table("t2", [Column("id", IntegerType()), Column("name", StringType())])

    with pytest.raises(TableError):
        intersect(t1, t2)


# ---------------------------------------------------------------------------
# 5. Валідація рядка не дозволяє додати некоректні дані
# ---------------------------------------------------------------------------
def test_table_row_validation():
    table = Table("t", [Column("id", IntegerType()), Column("score", RealType())])

    assert table.validate_row(["1", "4.5"]) is True
    assert table.validate_row(["not-a-number", "4.5"]) is False

    with pytest.raises(FieldTypeError):
        table.add_row(["not-a-number", "4.5"])

    # коректний рядок додається без помилок
    table.add_row(["1", "4.5"])
    assert len(table.rows) == 1
