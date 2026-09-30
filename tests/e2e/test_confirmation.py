import pytest
from textual.app import App

from lazyprox.screens import ConfirmationScreen
from tests.e2e.harness import APP_STYLES_PATH

pytestmark = pytest.mark.e2e


class Host(App[None]):
    CSS_PATH = APP_STYLES_PATH

    def __init__(self, screen: ConfirmationScreen) -> None:
        super().__init__()
        self.screen_under_test = screen

    def on_mount(self) -> None:
        self.push_screen(self.screen_under_test)


def test_short_question_dialog_snapshot(snap_compare):
    assert snap_compare(
        Host(ConfirmationScreen("Start 1 guest (1 VM)?")),
        terminal_size=(80, 24),
    )
