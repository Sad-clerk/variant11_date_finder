"""Unit-тесты чтения файлов и загрузки веб-страниц."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from date_finder.source_loader import (
    SourceLoadError,
    extract_visible_text,
    load_from_file,
    load_from_url,
)


class ExtractVisibleTextTests(unittest.TestCase):
    """Проверки извлечения читаемого текста из HTML."""

    def test_extracts_text_and_decodes_html_entities(self) -> None:
        html = "<html><body><p>Дата: 01.01.2024 &amp; праздник</p></body></html>"
        result = extract_visible_text(html)
        self.assertIn("Дата: 01.01.2024 & праздник", result)

    def test_skips_nested_hidden_tags(self) -> None:
        html = "<script>скрипт <style>скрытый текст</style></script>видимый текст"
        self.assertEqual(extract_visible_text(html), "видимый текст")

    def test_skips_script_style_and_noscript_content(self) -> None:
        html = (
            "<p>Видимая дата 01.01.2024</p>"
            "<script>31.12.2024</script>"
            "<style>30.11.2024</style>"
            "<noscript>29.10.2024</noscript>"
        )
        result = extract_visible_text(html)
        self.assertIn("01.01.2024", result)
        self.assertNotIn("31.12.2024", result)
        self.assertNotIn("30.11.2024", result)
        self.assertNotIn("29.10.2024", result)

    def test_empty_html_returns_empty_text(self) -> None:
        self.assertEqual(extract_visible_text(""), "")


class LoadFromFileTests(unittest.TestCase):
    """Проверки загрузки локальных текстовых файлов."""

    def test_reads_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.txt"
            path.write_text("Событие 01.01.2024", encoding="utf-8")
            self.assertEqual(load_from_file(path), "Событие 01.01.2024")

    def test_reads_utf8_bom_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.txt"
            path.write_text("Дата 02.02.2024", encoding="utf-8-sig")
            self.assertEqual(load_from_file(path), "Дата 02.02.2024")

    def test_reads_cp1251_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.txt"
            path.write_bytes("Событие 03.03.2024".encode("cp1251"))
            self.assertEqual(load_from_file(path), "Событие 03.03.2024")

    def test_missing_file_raises_source_load_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.txt"
            with self.assertRaises(SourceLoadError):
                load_from_file(path)

    def test_directory_path_raises_source_load_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SourceLoadError):
                load_from_file(directory)

    def test_file_read_error_is_converted_to_source_load_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.txt"
            path.write_text("Дата 01.01.2024", encoding="utf-8")
            with patch.object(
                Path,
                "read_text",
                side_effect=PermissionError("access denied"),
            ):
                with self.assertRaises(SourceLoadError):
                    load_from_file(path)


class LoadFromUrlTests(unittest.TestCase):
    """Проверки HTTP-загрузки с подменой сетевого запроса."""

    @staticmethod
    def make_response(html: str = "<p>Дата 04.04.2024</p>") -> Mock:
        response = Mock()
        response.text = html
        response.encoding = "utf-8"
        response.apparent_encoding = "utf-8"
        response.raise_for_status.return_value = None
        return response

    def test_loads_page_and_extracts_visible_text(self) -> None:
        response = self.make_response()
        with patch(
            "date_finder.source_loader.requests.get", return_value=response
        ) as get:
            result = load_from_url("https://example.com/news")

        self.assertIn("Дата 04.04.2024", result)
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["timeout"], 10.0)
        self.assertIn("User-Agent", get.call_args.kwargs["headers"])

    def test_trims_spaces_in_url(self) -> None:
        response = self.make_response()
        with patch(
            "date_finder.source_loader.requests.get", return_value=response
        ) as get:
            load_from_url("  https://example.com  ")
        self.assertEqual(get.call_args.args[0], "https://example.com")

    def test_rejects_invalid_url_without_http_request(self) -> None:
        with patch("date_finder.source_loader.requests.get") as get:
            with self.assertRaises(SourceLoadError):
                load_from_url("example.com/page")
        get.assert_not_called()

    def test_rejects_non_string_url(self) -> None:
        with self.assertRaises(SourceLoadError):
            load_from_url(None)  # type: ignore[arg-type]

    def test_http_error_is_converted_to_source_load_error(self) -> None:
        response = self.make_response()
        response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        with patch("date_finder.source_loader.requests.get", return_value=response):
            with self.assertRaises(SourceLoadError):
                load_from_url("https://example.com/missing")

    def test_timeout_is_converted_to_source_load_error(self) -> None:
        with patch(
            "date_finder.source_loader.requests.get",
            side_effect=requests.Timeout("connection timeout"),
        ):
            with self.assertRaises(SourceLoadError):
                load_from_url("https://example.com")


if __name__ == "__main__":
    unittest.main()
