"""
Модуль типів полів для міні-СУБД.

Кожен тип реалізує спільний інтерфейс FieldType:
    - validate(raw: str) -> bool       перевірка, чи можна розпарсити рядок у значення
    - parse(raw: str) -> Any           перетворення рядка у внутрішнє значення
    - to_string(value: Any) -> str     зворотне перетворення для відображення

Базові типи (обов'язкові для всіх варіантів): integer, real, char, string.
Додаткові типи (варіант 9): picture, realInvl.
"""

from __future__ import annotations
import os


class FieldTypeError(ValueError):
    """Помилка валідації/парсингу значення поля."""


class FieldType:
    """Абстрактний базовий клас для всіх типів полів."""

    name = "abstract"

    def validate(self, raw: str) -> bool:
        raise NotImplementedError

    def parse(self, raw: str):
        raise NotImplementedError

    def to_string(self, value) -> str:
        return str(value)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class IntegerType(FieldType):
    name = "integer"

    def validate(self, raw: str) -> bool:
        try:
            int(str(raw).strip())
            return True
        except (ValueError, TypeError):
            return False

    def parse(self, raw: str) -> int:
        if not self.validate(raw):
            raise FieldTypeError(f"'{raw}' не є цілим числом")
        return int(str(raw).strip())


class RealType(FieldType):
    name = "real"

    def validate(self, raw: str) -> bool:
        try:
            float(str(raw).strip())
            return True
        except (ValueError, TypeError):
            return False

    def parse(self, raw: str) -> float:
        if not self.validate(raw):
            raise FieldTypeError(f"'{raw}' не є дійсним числом")
        return float(str(raw).strip())


class CharType(FieldType):
    name = "char"

    def validate(self, raw: str) -> bool:
        return isinstance(raw, str) and len(raw) == 1

    def parse(self, raw: str) -> str:
        if not self.validate(raw):
            raise FieldTypeError(f"'{raw}' має бути рівно одним символом")
        return raw


class StringType(FieldType):
    name = "string"

    def validate(self, raw: str) -> bool:
        return isinstance(raw, str)

    def parse(self, raw: str) -> str:
        if not self.validate(raw):
            raise FieldTypeError(f"'{raw}' не є рядком")
        return raw


class PictureType(FieldType):
    """
    Тип 'picture' — зберігає шлях до файлу-зображення.
    Валідація: файл повинен існувати і мати дозволене розширення.
    """

    name = "picture"
    ALLOWED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

    def __init__(self, allowed_extensions=None, check_exists: bool = True):
        self.allowed_extensions = tuple(
            e.lower() for e in (allowed_extensions or self.ALLOWED_EXTENSIONS)
        )
        # check_exists=False корисно для unit-тестів без реальних файлів на диску
        self.check_exists = check_exists

    def validate(self, raw: str) -> bool:
        if not isinstance(raw, str) or not raw:
            return False
        _, ext = os.path.splitext(raw)
        if ext.lower() not in self.allowed_extensions:
            return False
        if self.check_exists and not os.path.isfile(raw):
            return False
        return True

    def parse(self, raw: str) -> str:
        if not self.validate(raw):
            raise FieldTypeError(
                f"'{raw}' не є коректним шляхом до зображення "
                f"(дозволені розширення: {self.allowed_extensions})"
            )
        return raw


class RealIntervalType(FieldType):
    """
    Тип 'realInvl' — інтервал дійсних чисел [min; max].
    Очікуваний формат вводу: "min;max" або "min:max" (пробіли ігноруються).
    """

    name = "realInvl"

    def _split(self, raw: str):
        raw = str(raw).strip()
        for sep in (";", ":", ","):
            if sep in raw:
                parts = raw.split(sep)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()
        return None

    def validate(self, raw) -> bool:
        if isinstance(raw, (tuple, list)) and len(raw) == 2:
            lo, hi = raw
            try:
                return float(lo) <= float(hi)
            except (TypeError, ValueError):
                return False
        parts = self._split(raw)
        if parts is None:
            return False
        lo_s, hi_s = parts
        try:
            lo, hi = float(lo_s), float(hi_s)
        except ValueError:
            return False
        return lo <= hi

    def parse(self, raw) -> tuple:
        if not self.validate(raw):
            raise FieldTypeError(
                f"'{raw}' не є коректним інтервалом (очікується 'min;max', min<=max)"
            )
        if isinstance(raw, (tuple, list)):
            return (float(raw[0]), float(raw[1]))
        lo_s, hi_s = self._split(raw)
        return (float(lo_s), float(hi_s))

    def to_string(self, value) -> str:
        lo, hi = value
        return f"[{lo}; {hi}]"


# Реєстр типів для (де)серіалізації бази з диску за назвою типу
TYPE_REGISTRY = {
    "integer": IntegerType,
    "real": RealType,
    "char": CharType,
    "string": StringType,
    "picture": PictureType,
    "realInvl": RealIntervalType,
}


def create_type(type_name: str) -> FieldType:
    """Фабрика: створити екземпляр типу поля за його іменем."""
    if type_name not in TYPE_REGISTRY:
        raise FieldTypeError(f"Невідомий тип поля: '{type_name}'")
    return TYPE_REGISTRY[type_name]()
