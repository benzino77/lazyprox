import pytest
from textual.app import App
from textual.widgets import Button, Select, SelectionList

from lazyprox.core.bulk import BulkGuest
from lazyprox.core.cluster_state import NodeState
from lazyprox.screens.bulk import BulkScreen
from tests.e2e.harness import APP_STYLES_PATH

pytestmark = pytest.mark.e2e

NODES = [
    NodeState("pve1", "online"),
    NodeState("pve2", "online"),
    NodeState("pve3", "offline"),
]
GUESTS = [
    BulkGuest(100, "db", "stopped", "qemu", "pve1"),
    BulkGuest(101, "web", "stopped", "lxc", "pve1"),
    BulkGuest(200, "app", "running", "qemu", "pve2"),
    BulkGuest(201, "cache", "running", "lxc", "pve2"),
    BulkGuest(300, "other", "stopped", "qemu", "pve3"),
]


class Host(App[None]):
    CSS_PATH = APP_STYLES_PATH

    def __init__(self, screen: BulkScreen) -> None:
        super().__init__()
        self.screen_under_test = screen
        self.result = "pending"

    def on_mount(self) -> None:
        self.push_screen(self.screen_under_test, self._done)

    def _done(self, result) -> None:
        self.result = result


def prompts(guest_list: SelectionList) -> list[str]:
    return [str(option.prompt) for option in guest_list.options]


def assert_rows_aligned(rows: list[str]) -> None:
    assert rows
    columns = set()
    for row in rows:
        assert len(row) <= 65
        fields = row.split()
        assert len(fields) == 5
        guest_type, node, status = fields[2], fields[3], fields[4]
        columns.add((row.index(guest_type), row.index(node), row.index(status)))
    assert len(columns) == 1


async def test_start_and_shutdown_rows_render_aligned_columns_within_budget():
    app = Host(BulkScreen(NODES, GUESTS))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        guest_list = app.screen.query_one("#bulk_guests", SelectionList)
        assert_rows_aligned(prompts(guest_list))

        app.screen.query_one("#bulk_operation", Select).value = "shutdown"
        await pilot.pause()
        assert_rows_aligned(prompts(guest_list))


def test_bulk_dialog_snapshot(snap_compare):
    assert snap_compare(
        Host(BulkScreen(NODES, GUESTS)),
        terminal_size=(100, 40),
    )


def test_bulk_migrate_dialog_snapshot(snap_compare):
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve1"))

    async def run_before(pilot):
        screen = pilot.app.screen
        screen.query_one("#bulk_operation", Select).value = "migrate"
        await pilot.pause()
        assert screen.query_one("#bulk_source", Select).value == "pve1"
        screen.query_one("#bulk_target", Select).value = "pve2"
        screen.query_one("#bulk_guests", SelectionList).select(("qemu", 100))
        await pilot.pause()

    assert snap_compare(app, terminal_size=(100, 40), run_before=run_before)


async def test_opens_on_start_with_nothing_checked_and_run_disabled():
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve1"))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, BulkScreen)
        assert screen.query_one("#bulk_operation", Select).value == "start"
        guest_list = screen.query_one("#bulk_guests", SelectionList)
        assert guest_list.selected == []
        assert screen.query_one("#bulk_run", Button).disabled
        shown = " ".join(prompts(guest_list))
        assert "100" in shown and "db" in shown and "VM" in shown and "pve1" in shown
        assert "101" in shown and "web" in shown and "LXC" in shown
        assert len(screen.query("#bulk_source")) == 0
        assert len(screen.query("#bulk_target")) == 0


async def test_operation_switch_clears_checks():
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve1"))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        guest_list = app.screen.query_one("#bulk_guests", SelectionList)
        guest_list.select(("qemu", 100))
        await pilot.pause()
        assert ("qemu", 100) in guest_list.selected

        app.screen.query_one("#bulk_operation", Select).value = "migrate"
        await pilot.pause()

        assert guest_list.selected == []
        assert ("qemu", 100) not in guest_list.selected
        shown = " ".join(prompts(guest_list))
        assert "db" in shown
        assert "pve2" not in shown


async def test_source_switch_clears_checks():
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve1"))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.screen.query_one("#bulk_operation", Select).value = "migrate"
        await pilot.pause()
        guest_list = app.screen.query_one("#bulk_guests", SelectionList)
        guest_list.select(("qemu", 100))
        await pilot.pause()
        assert guest_list.selected

        app.screen.query_one("#bulk_source", Select).value = "pve2"
        await pilot.pause()

        assert guest_list.selected == []
        shown = " ".join(prompts(guest_list))
        assert "app" in shown
        assert "db" not in shown


async def test_migrate_hidden_when_fewer_than_two_nodes_are_online():
    nodes = [NodeState("pve1", "online"), NodeState("pve3", "offline")]
    app = Host(BulkScreen(nodes, GUESTS))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        values = [value for _, value in app.screen.query_one("#bulk_operation", Select)._options]
        assert values == ["start", "shutdown"]


async def test_online_highlighted_node_prefills_source_and_run_waits_for_target():
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve1"))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.screen.query_one("#bulk_operation", Select).value = "migrate"
        await pilot.pause()

        source = app.screen.query_one("#bulk_source", Select)
        target = app.screen.query_one("#bulk_target", Select)
        assert source.value == "pve1"
        assert target.value == Select.NULL
        app.screen.query_one("#bulk_guests", SelectionList).select(("qemu", 100))
        await pilot.pause()
        run = app.screen.query_one("#bulk_run", Button)
        assert run.disabled

        target.value = "pve2"
        await pilot.pause()
        assert not run.disabled


async def test_offline_highlighted_node_does_not_prefill_source():
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve3"))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.screen.query_one("#bulk_operation", Select).value = "migrate"
        await pilot.pause()
        assert app.screen.query_one("#bulk_source", Select).value == Select.NULL
        assert app.screen.query_one("#bulk_guests", SelectionList).selected == []


async def test_source_change_clears_colliding_target():
    app = Host(BulkScreen(NODES, GUESTS, highlighted_node="pve1"))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.screen.query_one("#bulk_operation", Select).value = "migrate"
        await pilot.pause()
        target = app.screen.query_one("#bulk_target", Select)
        target.value = "pve2"
        await pilot.pause()
        app.screen.query_one("#bulk_source", Select).value = "pve2"
        await pilot.pause()
        assert target.value == Select.NULL
        assert app.screen.query_one("#bulk_run", Button).disabled


async def test_toggle_all_checks_then_clears():
    app = Host(BulkScreen(NODES, GUESTS))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        guest_list = app.screen.query_one("#bulk_guests", SelectionList)
        await pilot.press("a")
        await pilot.pause()
        assert len(guest_list.selected) == guest_list.option_count
        assert guest_list.option_count > 0
        assert not app.screen.query_one("#bulk_run", Button).disabled

        await pilot.press("a")
        await pilot.pause()
        assert guest_list.selected == []
        assert app.screen.query_one("#bulk_run", Button).disabled


async def test_escape_and_cancel_dismiss():
    app = Host(BulkScreen(NODES, GUESTS))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.result is None
        assert not isinstance(app.screen, BulkScreen)

    app = Host(BulkScreen(NODES, GUESTS))
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await pilot.click("#bulk_cancel")
        await pilot.pause()
        assert app.result is None
        assert not isinstance(app.screen, BulkScreen)
