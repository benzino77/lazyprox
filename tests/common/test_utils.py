from unittest.mock import MagicMock

import pytest

from lazyprox.common.utils import calculate_uptime, format_bytes, set_focus_border


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0d 0h 0m 0s"),
        (59, "0d 0h 0m 59s"),
        (60, "0d 0h 1m 0s"),
        (3661, "0d 1h 1m 1s"),
        (86400, "1d 0h 0m 0s"),
        (90061, "1d 1h 1m 1s"),
        (172801, "2d 0h 0m 1s"),
    ],
)
def test_calculate_uptime(seconds, expected):
    assert calculate_uptime(seconds) == expected


@pytest.mark.parametrize(
    "bytes_value, expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.00 KiB"),
        (1536, "1.50 KiB"),
        (1048576, "1.00 MiB"),
        (1572864, "1.50 MiB"),
        (1073741824, "1.00 GiB"),
        (1610612736, "1.50 GiB"),
    ],
)
def test_format_bytes(bytes_value, expected):
    assert format_bytes(bytes_value) == expected


def test_set_focus_border_removes_unfocused_and_adds_focused():
    widget_a = MagicMock()
    widget_b = MagicMock()
    handler = MagicMock()
    handler.screen.query.return_value = [widget_a, widget_b]

    set_focus_border(handler)

    handler.screen.query.assert_called_once_with("LeftColumn DataTable")
    for widget in (widget_a, widget_b):
        widget.remove_class.assert_called_once_with("focused", "unfocused")
        widget.add_class.assert_called_once_with("unfocused")
    handler.remove_class.assert_called_once_with("unfocused")
    handler.add_class.assert_called_once_with("focused", update=True)
