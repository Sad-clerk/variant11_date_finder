"""Проверка и поиск календарно корректных дат формата ДД.ММ.ГГГГ."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
import re


# Регулярное выражение проверяет структуру даты. Календарная проверка
# выполняется отдельно, чтобы учитывать длину месяцев и високосные годы.
DATE_PATTERN = re.compile(
    r"(?<![0-9])(?:0[1-9]|[12][0-9]|3[01])\."
    r"(?:0[1-9]|1[0-2])\.[0-9]{4}(?![0-9])"
)
DATE_COMPONENTS_PATTERN = re.compile(
    r"(?P<day>[0-9]{2})\.(?P<month>[0-9]{2})\.(?P<year>[0-9]{4})"
)

MONTH_NAMES = {
    1: "январе",
    2: "феврале",
    3: "марте",
    4: "апреле",
    5: "мае",
    6: "июне",
    7: "июле",
    8: "августе",
    9: "сентябре",
    10: "октябре",
    11: "ноябре",
    12: "декабре",
}


@dataclass(frozen=True)
class DateValidationResult:
    """Подробный результат проверки даты."""

    is_valid: bool
    message: str
    parsed_date: date | None = None
    is_future: bool = False
    is_today: bool = False


@dataclass(frozen=True)
class DateOccurrence:
    """Найденная корректная дата и её положение в исходном тексте."""

    value: str
    line: int
    column: int


def validate_date_detailed(
    value: str,
    today: date | None = None,
) -> DateValidationResult:
    """Проверяет формат и существование даты, объясняя причину ошибки.

    Если дата существует, дополнительно определяет, находится ли она
    в прошлом, сегодня или в будущем относительно параметра today.
    Если today не передан, используется текущая дата компьютера.
    """
    if not isinstance(value, str):
        return DateValidationResult(
            is_valid=False,
            message="Дата должна быть представлена текстовой строкой.",
        )

    match = DATE_COMPONENTS_PATTERN.fullmatch(value)
    if match is None:
        return DateValidationResult(
            is_valid=False,
            message=(
                "Дата некорректна: неверный формат. "
                "Используйте ДД.ММ.ГГГГ, например 05.09.2026."
            ),
        )

    day = int(match.group("day"))
    month = int(match.group("month"))
    year = int(match.group("year"))

    if not 1 <= day <= 31:
        return DateValidationResult(
            is_valid=False,
            message=(
                "Дата некорректна: день должен находиться "
                "в диапазоне от 01 до 31."
            ),
        )

    if not 1 <= month <= 12:
        return DateValidationResult(
            is_valid=False,
            message=(
                "Дата некорректна: месяц должен находиться "
                "в диапазоне от 01 до 12."
            ),
        )

    if year == 0:
        return DateValidationResult(
            is_valid=False,
            message=(
                "Дата некорректна: год должен находиться "
                "в диапазоне от 0001 до 9999."
            ),
        )

    try:
        parsed_date = date(year, month, day)
    except ValueError:
        days_in_month = monthrange(year, month)[1]
        month_name = MONTH_NAMES[month]
        return DateValidationResult(
            is_valid=False,
            message=(
                f"Дата некорректна: в {month_name} {year} года "
                f"{days_in_month} дней, поэтому дата {value} не существует."
            ),
        )

    comparison_date = today if today is not None else date.today()

    if parsed_date > comparison_date:
        return DateValidationResult(
            is_valid=True,
            message=f"Дата {value} корректна, но относится к будущему.",
            parsed_date=parsed_date,
            is_future=True,
        )

    if parsed_date == comparison_date:
        return DateValidationResult(
            is_valid=True,
            message=f"Дата {value} корректна. Это сегодняшний день.",
            parsed_date=parsed_date,
            is_today=True,
        )

    return DateValidationResult(
        is_valid=True,
        message=f"Дата {value} корректна.",
        parsed_date=parsed_date,
    )


def validate_date(value: str) -> bool:
    """Возвращает True, если value — существующая дата ДД.ММ.ГГГГ."""
    return validate_date_detailed(value).is_valid


def find_valid_dates(text: str) -> list[DateOccurrence]:
    """Находит все календарно корректные даты в тексте.

    Повторяющиеся даты сохраняются. Нумерация строк и столбцов начинается
    с единицы. Числовые фрагменты внутри более длинных чисел не учитываются.
    """
    if not isinstance(text, str):
        raise TypeError("Параметр text должен иметь тип str.")

    occurrences: list[DateOccurrence] = []

    for match in DATE_PATTERN.finditer(text):
        date_value = match.group(0)
        if not validate_date(date_value):
            continue

        line = text.count("\n", 0, match.start()) + 1
        previous_newline = text.rfind("\n", 0, match.start())
        column = match.start() - previous_newline
        occurrences.append(
            DateOccurrence(value=date_value, line=line, column=column)
        )

    return occurrences
