"""Загрузка текста из локального файла или веб-страницы."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests


class SourceLoadError(Exception):
    """Ошибка при чтении файла или загрузке веб-страницы."""


class _VisibleTextParser(HTMLParser):
    """Извлекает видимый текст HTML, пропуская содержимое script/style."""

    _BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div",
        "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li",
        "main", "nav", "ol", "p", "pre", "section", "table", "td",
        "th", "tr", "ul",
    }
    _SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs  # Атрибуты не являются видимым текстом страницы.
        if self._skip_depth:
            if tag in self._SKIP_TAGS:
                self._skip_depth += 1
            return

        if tag in self._SKIP_TAGS:
            self._skip_depth = 1
        elif tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in self._SKIP_TAGS:
                self._skip_depth -= 1
            return

        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def extract_visible_text(html: str) -> str:
    """Преобразует HTML в текст, который можно передать поиску дат."""
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)


def load_from_file(file_path: str | Path) -> str:
    """Читает текстовый файл в UTF-8 или Windows-1251."""
    path = Path(file_path).expanduser()

    if not path.exists():
        raise SourceLoadError(f"Файл не найден: {path}")
    if not path.is_file():
        raise SourceLoadError(f"Указанный путь не является файлом: {path}")

    try:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return path.read_text(encoding="cp1251")
    except OSError as error:
        raise SourceLoadError(f"Ошибка чтения файла: {error}") from error


def load_from_url(url: str, timeout: float = 10.0) -> str:
    """Загружает веб-страницу по HTTP(S) и возвращает её видимый текст."""
    if not isinstance(url, str):
        raise SourceLoadError("Адрес страницы должен быть строкой.")

    normalized_url = url.strip()
    parsed_url = urlparse(normalized_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise SourceLoadError(
            "Некорректный адрес. Укажите полный URL с http:// или https://."
        )

    try:
        response = requests.get(
            normalized_url,
            timeout=timeout,
            headers={"User-Agent": "Variant11DateFinder/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise SourceLoadError(f"Не удалось загрузить страницу: {error}") from error

    # apparent_encoding помогает корректно прочитать страницы без charset.
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return extract_visible_text(response.text)
