"""Tests for the code extractor."""

import pytest

from digital_ichthyologist.extractor import BlockInfo, get_functions_and_classes


SIMPLE_SOURCE = """\
def greet(name):
    return f"Hello, {name}!"


def add(a, b):
    return a + b
"""

CLASS_SOURCE = """\
class Animal:
    def speak(self):
        sound = "..."
        return sound

    def move(self):
        direction = "forward"
        speed = 1
        return direction, speed


def standalone():
    x = 1
    y = 2
    return x + y
"""

SYNTAX_ERROR_SOURCE = "def broken(:\n    pass\n"

ASYNC_SOURCE = """\
async def fetch(url):
    import asyncio
    await asyncio.sleep(0)
    return url
"""


class TestGetFunctionsAndClasses:
    def test_extracts_top_level_functions(self):
        result = get_functions_and_classes(SIMPLE_SOURCE)
        assert "greet" in result
        assert "add" in result

    def test_function_content_present(self):
        result = get_functions_and_classes(SIMPLE_SOURCE)
        assert "Hello" in result["greet"].source

    def test_extracts_class(self):
        result = get_functions_and_classes(CLASS_SOURCE)
        assert "Animal" in result

    def test_extracts_methods(self):
        result = get_functions_and_classes(CLASS_SOURCE)
        assert "Animal.speak" in result
        assert "Animal.move" in result

    def test_standalone_function_with_class(self):
        result = get_functions_and_classes(CLASS_SOURCE)
        assert "standalone" in result

    def test_no_classes_when_disabled(self):
        result = get_functions_and_classes(CLASS_SOURCE, include_classes=False)
        assert "Animal" not in result
        # But methods should still NOT be included without the class
        # (include_methods only adds methods when include_classes is True or
        # the class body is traversed)

    def test_no_methods_when_disabled(self):
        result = get_functions_and_classes(CLASS_SOURCE, include_methods=False)
        assert "Animal.speak" not in result
        assert "Animal.move" not in result
        assert "Animal" in result  # class itself still included

    def test_syntax_error_returns_empty(self):
        result = get_functions_and_classes(SYNTAX_ERROR_SOURCE)
        assert result == {}

    def test_empty_source_returns_empty(self):
        result = get_functions_and_classes("")
        assert result == {}

    def test_async_function_extracted(self):
        result = get_functions_and_classes(ASYNC_SOURCE)
        assert "fetch" in result

    def test_method_content_dedented(self):
        result = get_functions_and_classes(CLASS_SOURCE)
        # The extracted method should start at column 0 (after dedent)
        first_line = result["Animal.speak"].source.splitlines()[0]
        assert not first_line.startswith("    ")

    def test_returns_block_info_with_line_numbers(self):
        result = get_functions_and_classes(SIMPLE_SOURCE)
        info = result["greet"]
        assert isinstance(info, BlockInfo)
        assert info.start_line == 1
        assert info.end_line == 2

    def test_class_line_numbers(self):
        result = get_functions_and_classes(CLASS_SOURCE)
        info = result["Animal"]
        assert info.start_line == 1
        assert info.end_line == 9

    def test_method_line_numbers(self):
        result = get_functions_and_classes(CLASS_SOURCE)
        info = result["Animal.speak"]
        assert info.start_line == 2
        assert info.end_line == 4
