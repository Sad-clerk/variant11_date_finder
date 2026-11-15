"""Консольный пользовательский интерфейс программы."""

from date_finder.source_loader import (
    SourceLoadError,
    load_from_file,
    load_from_url,
)
from date_finder.validator import find_valid_dates, validate_date_detailed


def _print_search_results(text: str) -> None:
    """Выводит результаты поиска дат с указанием строк и столбцов."""
    occurrences = find_valid_dates(text)

    if not occurrences:
        print("Корректные даты формата ДД.ММ.ГГГГ не найдены.")
        return

    print(f"Найдено корректных дат: {len(occurrences)}")
    for number, occurrence in enumerate(occurrences, start=1):
        validation = validate_date_detailed(occurrence.value)
        status = " — относится к будущему" if validation.is_future else ""
        if validation.is_today:
            status = " — сегодняшняя дата"
        print(
            f"{number}. {occurrence.value}{status} "
            f"(строка {occurrence.line}, столбец {occurrence.column})"
        )


def _check_user_date() -> None:
    """Проверяет дату, введённую пользователем."""
    user_date = input("Введите дату в формате ДД.ММ.ГГГГ: ").strip()
    validation = validate_date_detailed(user_date)
    print(validation.message)


def _search_file() -> None:
    """Загружает файл и запускает поиск дат в его содержимом."""
    file_path = input("Введите путь к текстовому файлу: ").strip()
    try:
        text = load_from_file(file_path)
    except SourceLoadError as error:
        print(f"Ошибка: {error}")
        return

    print(f"\nРезультаты поиска в файле «{file_path}»:")
    _print_search_results(text)


def _search_web_page() -> None:
    """Загружает веб-страницу и запускает поиск дат в её тексте."""
    url = input("Введите URL веб-страницы: ").strip()
    try:
        text = load_from_url(url)
    except SourceLoadError as error:
        print(f"Ошибка: {error}")
        return

    print(f"\nРезультаты поиска на странице {url}:")
    _print_search_results(text)


def run_cli() -> None:
    """Запускает главное меню программы."""
    print("=" * 58)
    print("ПОИСК И ПРОВЕРКА ДАТ — ВАРИАНТ 11")
    print("Формат даты: ДД.ММ.ГГГГ")
    print("=" * 58)

    actions = {
        "1": _check_user_date,
        "2": _search_file,
        "3": _search_web_page,
    }

    while True:
        print("\nВыберите действие:")
        print("1 — Проверить введённую дату")
        print("2 — Найти даты в файле")
        print("3 — Найти даты на веб-странице по URL")
        print("0 — Выход")

        choice = input("Ваш выбор: ").strip()
        if choice == "0":
            print("Работа программы завершена.")
            break

        action = actions.get(choice)
        if action is None:
            print("Неизвестная команда. Выберите пункт от 0 до 3.")
            continue

        action()
