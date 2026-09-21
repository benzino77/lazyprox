from unittest.mock import MagicMock

import pytest
from textual.color import Color

from lazyprox.common import Config
from lazyprox.widgets.details_views import GraphWidget, NodeGraphWidget
from tests.e2e import make_app, wait_for_server_selection

pytestmark = pytest.mark.e2e

THEMED_TOML = """\
[[server]]
name = "proxmox-alpha"
host = "192.168.1.10"
user = "root"
realm = "pam"
token_name = "test"
token_value = "secret-a"

[[server]]
name = "proxmox-beta"
host = "192.168.1.20"
user = "root"
realm = "pam"
token_name = "test"
token_value = "secret-b"

[theme]
primary = "#BB9AF7"
secondary = "#7AA2F7"
accent = "#FF9E64"
warning = "#E0AF68"
error = "#F7768E"
success = "#9ECE6A"
foreground = "#a9b1d6"
background = "#1A1B26"
surface = "#24283B"
panel = "#414868"
"""


def _load_themed_config(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(THEMED_TOML)
    Config.load_config(config_file_path=str(config_file))


def _make_graph_widget() -> GraphWidget:
    return GraphWidget(
        graph_title="CPU",
        data_x_label="Time",
        data_y_label="%",
        series_1_label="CPU",
        series_2_label="IOd",
    )


def test_app_applies_configured_theme(tmp_path):
    _load_themed_config(tmp_path)

    app = make_app()

    assert app.theme == "lazyprox"
    assert app.get_theme("lazyprox").primary == "#BB9AF7"
    assert app.get_theme("lazyprox").accent == "#FF9E64"
    assert app.get_theme("lazyprox").dark is True


def test_app_keeps_default_theme_without_theme_section():
    app = make_app()

    assert app.theme == "textual-dark"


async def test_graph_series_colors_follow_theme(tmp_path):
    _load_themed_config(tmp_path)

    app = make_app()
    async with app.run_test() as pilot:
        await wait_for_server_selection(pilot)
        widget = _make_graph_widget()
        await app.screen.mount(widget)
        await pilot.pause()

        plot = MagicMock()
        widget.plt.plot = plot
        widget.set_data([1.0], 2.0, [1.0], 2.0, [1.0], 2.0, [1.0], 2.0)

        assert app.theme_variables["primary"] == "#BB9AF7"
        assert len(plot.call_args_list) == 2
        assert plot.call_args_list[0].kwargs["color"] == Color.parse(app.theme_variables["primary"]).rgb
        assert plot.call_args_list[1].kwargs["color"] == Color.parse(app.theme_variables["accent"]).rgb


async def test_graph_series_use_default_colors_without_theme():
    app = make_app()
    async with app.run_test() as pilot:
        await wait_for_server_selection(pilot)
        widget = _make_graph_widget()
        await app.screen.mount(widget)
        await pilot.pause()

        plot = MagicMock()
        widget.plt.plot = plot
        widget.set_data([1.0], 2.0, [1.0], 2.0, [1.0], 2.0, [1.0], 2.0)

        assert len(plot.call_args_list) == 2
        assert "color" not in plot.call_args_list[0].kwargs
        assert "color" not in plot.call_args_list[1].kwargs


@pytest.mark.parametrize("with_theme", [True, False])
async def test_graph_views_render_with_config(tmp_path, with_theme):
    if with_theme:
        _load_themed_config(tmp_path)

    app = make_app()
    async with app.run_test() as pilot:
        await wait_for_server_selection(pilot)
        view = NodeGraphWidget()
        await app.screen.mount(view)
        await pilot.pause()

        for graph in view.query(GraphWidget):
            graph.set_data([1.0], 2.0, [1.0], 2.0, [1.0], 2.0, [1.0], 2.0)
