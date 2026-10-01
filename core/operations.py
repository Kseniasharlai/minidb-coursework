"""
Модуль operations.py — операції над парами таблиць.

Індивідуальна операція варіанту: ПЕРЕТИН ТАБЛИЦЬ (INTERSECT).
Результат — нова таблиця з тією ж схемою, що містить лише ті рядки,
які одночасно присутні в обох вихідних таблицях (за повним збігом значень).
"""

from __future__ import annotations
from .table import Table, TableError


def intersect(table1: Table, table2: Table, result_name: str | None = None) -> Table:
    """
    Обчислює перетин двох таблиць з однаковою схемою.

    :param table1: перша таблиця
    :param table2: друга таблиця
    :param result_name: ім'я результуючої таблиці (за замовчуванням генерується)
    :raises TableError: якщо схеми таблиць не збігаються
    :return: нова таблиця-результат (не додається автоматично в жодну Database)
    """
    if not table1.has_same_schema(table2):
        raise TableError(
            f"Неможливо виконати перетин: таблиці '{table1.name}' і '{table2.name}' "
            f"мають різні схеми"
        )

    name = result_name or f"{table1.name}_INTERSECT_{table2.name}"
    result = Table(name, list(table1.columns))

    rows2 = table2.get_rows()
    seen = set()
    for row in table1.get_rows():
        key = tuple(row.values)
        if key in seen:
            continue  # уникнення дублікатів у результаті
        if any(row.values == r2.values for r2 in rows2):
            result.rows.append(row)
            seen.add(key)

    return result
