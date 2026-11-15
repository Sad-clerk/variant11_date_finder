"""Unit-тесты основных сценариев консольного интерфейса."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import patch

from date_finder import cli
from date_finder.source_loader import SourceLoadError
from date_finder.validator import DateValidationResult


class CliTests(unittest.TestCase):
    """Проверка переходов меню и обработки пользовательских действий."""

    def run_with_inputs(self, inputs: list[str]) -> str:
        output = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            cli.run_cli()
        return output.getvalue()

    def test_exit_command(self) -> None:
        output = self.run_with_inputs(["0"])
        self.assertIn("Работа программы завершена.", output)

    def test_unknown_command_does_not_stop_program(self) -> None:
        output = self.run_with_inputs(["9", "0"])
        self.assertIn("Неизвестная команда", output)
        self.assertIn("Работа программы завершена.", output)

    def test_manual_valid_date(self) -> None:
        output = self.run_with_inputs(["1", "29.02.2024", "0"])
        self.assertIn("Дата 29.02.2024 корректна.", output)

    def test_manual_invalid_date_explains_reason(self) -> None:
        output = self.run_with_inputs(["1", "29.02.2023", "0"])
        self.assertIn("Дата некорректна", output)
        self.assertIn("в феврале 2023 года 28 дней", output)

    def test_manual_future_date_is_reported(self) -> None:
        future_result = DateValidationResult(
            is_valid=True,
            message="Дата 01.01.2028 корректна, но относится к будущему.",
            parsed_date=date(2028, 1, 1),
            is_future=True,
        )
        with patch.object(
            cli, "validate_date_detailed", return_value=future_result
        ):
            output = self.run_with_inputs(["1", "01.01.2028", "0"])
        self.assertIn("Дата 01.01.2028 корректна, но относится к будущему", output)

    def test_search_file_success(self) -> None:
        with patch.object(cli, "load_from_file", return_value="Дата 10.11.2026"):
            output = self.run_with_inputs(["2", "dates.txt", "0"])
        self.assertIn("Результаты поиска в файле", output)
        self.assertIn("10.11.2026", output)

    def test_search_result_marks_future_date(self) -> None:
        future_result = DateValidationResult(
            is_valid=True,
            message="Дата 01.01.2028 корректна, но относится к будущему.",
            parsed_date=date(2028, 1, 1),
            is_future=True,
        )
        with patch.object(
            cli, "validate_date_detailed", return_value=future_result
        ):
            with patch.object(
                cli, "load_from_file", return_value="Дата 01.01.2028"
            ):
                output = self.run_with_inputs(["2", "dates.txt", "0"])
        self.assertIn("относится к будущему", output)

    def test_search_file_error(self) -> None:
        with patch.object(
            cli, "load_from_file", side_effect=SourceLoadError("Файл не найден")
        ):
            output = self.run_with_inputs(["2", "missing.txt", "0"])
        self.assertIn("Ошибка: Файл не найден", output)

    def test_search_url_success(self) -> None:
        with patch.object(cli, "load_from_url", return_value="Дата 10.11.2026"):
            output = self.run_with_inputs(["3", "https://example.com", "0"])
        self.assertIn("Результаты поиска на странице", output)
        self.assertIn("10.11.2026", output)

    def test_search_url_error(self) -> None:
        with patch.object(
            cli, "load_from_url", side_effect=SourceLoadError("Сайт недоступен")
        ):
            output = self.run_with_inputs(["3", "https://example.com", "0"])
        self.assertIn("Ошибка: Сайт недоступен", output)

    def test_no_results_message(self) -> None:
        with patch.object(cli, "load_from_file", return_value="Здесь нет дат"):
            output = self.run_with_inputs(["2", "empty.txt", "0"])
        self.assertIn("Корректные даты формата ДД.ММ.ГГГГ не найдены", output)


if __name__ == "__main__":
    unittest.main()
