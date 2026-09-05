from textual.pilot import Pilot

from lazyprox.app import LazyProx
from lazyprox.screens import ServerSelectionScreen


def make_app() -> LazyProx:
    return LazyProx()


async def wait_for_server_selection(pilot: Pilot) -> None:
    for _ in range(50):
        if isinstance(pilot.app.screen, ServerSelectionScreen):
            return
        await pilot.pause()
    raise AssertionError(
        f"Expected ServerSelectionScreen, got {type(pilot.app.screen).__name__}"
    )
