import pytest
from textual.widgets import Select

from lazyprox.common import Config
from tests.e2e import make_app, wait_for_server_selection

pytestmark = pytest.mark.e2e


def test_e2e_config_has_multiple_servers():
    assert Config.configuration is not None
    assert len(Config.configuration["server"]) >= 2


def test_server_selection_screen_snapshot(snap_compare):
    async def run_before(pilot):
        await wait_for_server_selection(pilot)

    assert snap_compare(
        make_app(),
        terminal_size=(80, 24),
        run_before=run_before,
    )


async def test_server_select_options_match_config():
    app = make_app()
    async with app.run_test() as pilot:
        await wait_for_server_selection(pilot)
        server_select = app.screen.query_one("#server_select", Select)
        actual = [
            (label, value)
            for label, value in server_select._options
            if value is not Select.NULL
        ]
        expected = [
            (server["name"], idx)
            for idx, server in enumerate(Config.configuration["server"])
        ]
        assert actual == expected


async def test_quit_launch_screen_with_ctrl_q():
    app = make_app()
    async with app.run_test() as pilot:
        await wait_for_server_selection(pilot)
        await pilot.press("ctrl+q")
        await pilot.pause()
        assert app.return_code == 0
