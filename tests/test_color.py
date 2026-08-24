from __future__ import annotations

import pytest
from pathlib import Path

from pymfcad.backend import Color


def test_color_imports():
    from pymfcad.backend.color import parse_colors_from_text

    parse_colors_from_text(Path("tests/data/base_colors.csv"))


def test_color_from_name_and_str():
    color = Color.from_name("aqua", 128)
    assert color._to_rgba()[3] == 128
    assert str(color).startswith("rgba(")


def test_color_from_matplotlib_cycle():
    color = Color.from_name("c0", 200)
    assert color._to_rgba()[3] == 200
    assert str(color).startswith("rgba(")


def test_color_from_hex_and_rgba():
    color = Color.from_hex("#ff0000")
    assert color._to_rgba() == (255, 0, 0, 255)

    color_with_alpha = Color.from_hex("00ff0080")
    assert color_with_alpha._to_rgba() == (0, 255, 0, 128)

    color_rgba = Color.from_rgba((1, 2, 3, 4))
    assert color_rgba._to_rgba() == (1, 2, 3, 4)


def test_color_from_rgba_percent():
    color = Color.from_rgba_percent((0.5, 0.0, 1.0, 0.25))
    assert color._to_rgba() == (127, 0, 255, 63)


def test_color_clamp_and_repr():
    color = Color(300, -10, 10.5, 999)
    assert color._to_rgba() == (255, 0, 10, 255)
    assert "Color(r=" in repr(color)


def test_color_invalid_inputs():
    with pytest.raises(ValueError):
        Color.from_rgba((1, 2, 3))
    with pytest.raises(ValueError):
        Color.from_rgba_percent((0.1, 0.2, 0.3))
    with pytest.raises(ValueError):
        Color.from_hex("12345")
    with pytest.raises(ValueError):
        Color.from_name("not_a_color")
