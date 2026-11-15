"""Unit-тесты проверки и поиска дат."""

import unittest
from datetime import date

from date_finder.validator import (
    DATE_PATTERN,
    DateOccurrence,
    find_valid_dates,
    validate_date,
    validate_date_detailed,
)


class ValidateDateTests(unittest.TestCase):
    """Проверки корректности отдельной даты."""

    def test_valid_regular_dates(self) -> None:
        for value in ("01.01.2024", "31.01.2024", "30.04.2023", "15.12.9999"):
            with self.subTest(value=value):
                self.assertTrue(validate_date(value))

    def test_valid_leap_day(self) -> None:
        self.assertTrue(validate_date("29.02.2024"))
        self.assertTrue(validate_date("29.02.2000"))

    def test_invalid_leap_day(self) -> None:
        self.assertFalse(validate_date("29.02.2023"))
        self.assertFalse(validate_date("29.02.1900"))

    def test_invalid_day_for_month(self) -> None:
        for value in ("31.04.2024", "31.06.2024", "30.02.2024", "31.02.2024"):
            with self.subTest(value=value):
                self.assertFalse(validate_date(value))

    def test_invalid_day_and_month_ranges(self) -> None:
        for value in (
            "00.01.2024", "32.01.2024", "01.00.2024", "01.13.2024",
            "01.01.0000",
        ):
            with self.subTest(value=value):
                self.assertFalse(validate_date(value))

    def test_format_must_have_leading_zeroes_and_four_digit_year(self) -> None:
        for value in ("1.01.2024", "01.1.2024", "1.1.2024", "01.01.24"):
            with self.subTest(value=value):
                self.assertFalse(validate_date(value))

    def test_non_date_strings_are_rejected(self) -> None:
        for value in (
            "", "today", "2024-01-01", "01/01/2024", " 01.01.2024",
            "٠١.٠١.٢٠٢٤",
        ):
            with self.subTest(value=value):
                self.assertFalse(validate_date(value))

    def test_non_string_value_is_rejected(self) -> None:
        self.assertFalse(validate_date(None))  # type: ignore[arg-type]
        self.assertFalse(validate_date(20241110))  # type: ignore[arg-type]

    def test_pattern_matches_only_expected_structure(self) -> None:
        self.assertIsNotNone(DATE_PATTERN.fullmatch("09.11.2026"))
        self.assertIsNone(DATE_PATTERN.fullmatch("9.11.2026"))
        # 31 февраля проходит regex, но не календарную проверку.
        self.assertIsNotNone(DATE_PATTERN.fullmatch("31.02.2024"))
        self.assertFalse(validate_date("31.02.2024"))


class DetailedDateValidationTests(unittest.TestCase):
    """Проверки пояснений и определения будущих дат."""

    def test_explains_invalid_leap_day(self) -> None:
        result = validate_date_detailed("29.02.2023", today=date(2026, 11, 10))
        self.assertFalse(result.is_valid)
        self.assertIn("в феврале 2023 года 28 дней", result.message)

    def test_explains_invalid_day_for_month(self) -> None:
        result = validate_date_detailed("31.04.2024", today=date(2026, 11, 10))
        self.assertFalse(result.is_valid)
        self.assertIn("в апреле 2024 года 30 дней", result.message)

    def test_explains_day_range(self) -> None:
        result = validate_date_detailed("32.01.2024", today=date(2026, 11, 10))
        self.assertIn("день должен находиться", result.message)

    def test_explains_month_range(self) -> None:
        result = validate_date_detailed("01.13.2024", today=date(2026, 11, 10))
        self.assertIn("месяц должен находиться", result.message)

    def test_explains_wrong_format(self) -> None:
        result = validate_date_detailed("01.01.24", today=date(2026, 11, 10))
        self.assertIn("неверный формат", result.message)

    def test_future_date_is_valid_and_marked_as_future(self) -> None:
        result = validate_date_detailed("01.01.2028", today=date(2026, 11, 10))
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_future)
        self.assertFalse(result.is_today)
        self.assertIn("корректна, но относится к будущему", result.message)

    def test_today_is_marked_separately(self) -> None:
        result = validate_date_detailed("10.11.2026", today=date(2026, 11, 10))
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_today)
        self.assertFalse(result.is_future)
        self.assertIn("сегодняшний день", result.message)

    def test_past_date_is_valid_without_future_marker(self) -> None:
        result = validate_date_detailed("09.11.2026", today=date(2026, 11, 10))
        self.assertTrue(result.is_valid)
        self.assertFalse(result.is_future)
        self.assertFalse(result.is_today)
        self.assertEqual(result.message, "Дата 09.11.2026 корректна.")


class FindValidDatesTests(unittest.TestCase):
    """Проверки поиска дат в произвольном тексте."""

    def test_finds_one_date(self) -> None:
        result = find_valid_dates("Дата публикации: 09.11.2026.")
        self.assertEqual(result, [DateOccurrence("09.11.2026", 1, 18)])

    def test_finds_multiple_dates_and_preserves_duplicates(self) -> None:
        text = "Первая: 01.01.2024\nВторая: 29.02.2024\nПовтор: 01.01.2024"
        result = find_valid_dates(text)
        self.assertEqual(
            [item.value for item in result],
            ["01.01.2024", "29.02.2024", "01.01.2024"],
        )
        self.assertEqual([item.line for item in result], [1, 2, 3])

    def test_returns_correct_columns(self) -> None:
        result = find_valid_dates("abc 05.06.2024\nxy 07.08.2025")
        self.assertEqual([item.column for item in result], [5, 4])

    def test_ignores_impossible_dates(self) -> None:
        text = "31.02.2024 29.02.2023 31.04.2024 01.01.2024"
        result = find_valid_dates(text)
        self.assertEqual([item.value for item in result], ["01.01.2024"])

    def test_does_not_match_date_inside_longer_number(self) -> None:
        text = "12301.01.2024 01.01.20245 01.01.2024"
        result = find_valid_dates(text)
        self.assertEqual([item.value for item in result], ["01.01.2024"])

    def test_empty_text_returns_empty_list(self) -> None:
        self.assertEqual(find_valid_dates(""), [])

    def test_text_must_be_string(self) -> None:
        with self.assertRaises(TypeError):
            find_valid_dates(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
