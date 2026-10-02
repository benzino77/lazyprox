import pytest
from textual.app import App
from textual.widgets import Select

from lazyprox.screens.select_destination import DestinationSelectionScreen
from tests.e2e.harness import APP_STYLES_PATH

pytestmark = pytest.mark.e2e

NODES = ["pve2", "pve3"]


class Host(App[None]):
    CSS_PATH = APP_STYLES_PATH

    def __init__(self, screen: DestinationSelectionScreen) -> None:
        super().__init__()
        self.screen_under_test = screen
        self.result = "pending"

    def on_mount(self) -> None:
        self.push_screen(self.screen_under_test, self._done)

    def _done(self, result) -> None:
        self.result = result


async def test_destination_options_exclude_source_and_have_no_preselection():
    app = Host(DestinationSelectionScreen("db", NODES))
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        select = app.screen.query_one("#destination_select", Select)
        values = [value for _, value in select._options if value is not Select.NULL]
        assert values == ["pve2", "pve3"]
        assert "pve1" not in values
        assert select.value is Select.NULL


async def test_choosing_destination_dismisses_with_node_name():
    app = Host(DestinationSelectionScreen("db", NODES))
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        app.screen.query_one("#destination_select", Select).value = "pve3"
        await pilot.pause()
        assert app.result == "pve3"


async def test_escape_dismisses_with_none():
    app = Host(DestinationSelectionScreen("db", NODES))
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.result is None
        assert not isinstance(app.screen, DestinationSelectionScreen)


def test_destination_dialog_snapshot(snap_compare):
    assert snap_compare(
        Host(DestinationSelectionScreen("db", NODES)),
        terminal_size=(80, 24),
    )
