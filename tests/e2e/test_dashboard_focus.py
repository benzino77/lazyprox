from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from textual.widgets import Input

from lazyprox.app import LazyProx
from lazyprox.data import ProxmoxData
from lazyprox.screens import DashboardScreen, FilterScreen
from lazyprox.widgets import DetailsWidget, LxcWidget, NodeWidget, QemuWidget
from lazyprox.widgets.details_views import NodeTasksWidget

pytestmark = pytest.mark.e2e

TASKS = [
    {
        "starttime": 1759700000,
        "endtime": 1759700100,
        "type": "qmstart",
        "id": 100,
        "node": "pve1",
        "user": "root@pam",
        "status": "OK",
        "upid": "UPID:pve1:0001",
    },
    {
        "starttime": 1759690000,
        "endtime": 0,
        "type": "vzdump",
        "id": 101,
        "node": "pve1",
        "user": "root@pam",
        "status": "running",
        "upid": "UPID:pve1:0002",
    },
]


def make_resources() -> dict:
    return {
        "nodes": [
            {"node": "pve1", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
            {"node": "pve2", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
        ],
        "nodes/pve1/status": {},
        "nodes/pve2/status": {},
        "nodes/pve1/lxc": [{"vmid": 101, "name": "ct1", "status": "running", "template": 0}],
        "nodes/pve2/lxc": [],
        "nodes/pve1/qemu": [{"vmid": 100, "name": "vm1", "status": "running", "template": 0}],
        "nodes/pve2/qemu": [],
        "cluster/tasks": [dict(task) for task in TASKS],
    }


@pytest.fixture
def seeded_proxmox():
    previous = ProxmoxData.p_prox_resources
    ProxmoxData.p_prox_resources = make_resources()
    yield
    ProxmoxData.p_prox_resources = previous


def dashboard_mount(self) -> None:
    self.push_screen("dashboard")


async def wait_for_type(pilot, screen_type):
    for _ in range(50):
        if isinstance(pilot.app.screen, screen_type):
            await pilot.pause()
            return
        await pilot.pause()
    raise AssertionError(f"Expected {screen_type.__name__}, got {type(pilot.app.screen).__name__}")


@asynccontextmanager
async def dashboard_app():
    app = LazyProx()
    with patch.object(LazyProx, "on_mount", dashboard_mount):
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            yield app, pilot


async def focus_nodes_table(app, pilot) -> NodeWidget:
    nodes = app.screen.query_one(NodeWidget)
    for widget in (nodes, app.screen.query_one(LxcWidget), app.screen.query_one(QemuWidget)):
        widget.update_table_data()
    if nodes.row_count:
        nodes.move_cursor(row=0)
    app.screen.set_focus(nodes)
    await pilot.pause()
    return nodes


async def show_tasks_view(pilot) -> None:
    # the node details modes rotate summary -> graphs -> tasks with `d`
    await pilot.press("d")
    await pilot.pause()
    await pilot.press("d")
    await pilot.pause()


async def open_filter_dialog(pilot) -> None:
    await pilot.press("f")
    for _ in range(20):
        if isinstance(pilot.app.screen, FilterScreen):
            await pilot.pause()
            return
        await pilot.pause()
    raise AssertionError(f"Expected FilterScreen, got {type(pilot.app.screen).__name__}")


async def test_focus_panes_order_with_and_without_tasks(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        qemu = app.screen.query_one(QemuWidget)
        tasks = app.screen.query_one(NodeTasksWidget)
        details = app.screen.query_one(DetailsWidget)

        assert details.current == "node_summary_widget"
        assert app.screen.focus_panes() == [nodes, lxc, qemu]

        await show_tasks_view(pilot)
        assert details.current == "node_tasks_widget"
        assert app.screen.focus_panes() == [nodes, tasks, lxc, qemu]

        await pilot.press("d")
        await pilot.pause()
        assert details.current == "node_summary_widget"
        assert app.screen.focus_panes() == [nodes, lxc, qemu]


async def test_tab_forward_cycle_with_tasks_displayed(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        qemu = app.screen.query_one(QemuWidget)
        tasks = app.screen.query_one(NodeTasksWidget)
        details = app.screen.query_one(DetailsWidget)

        await show_tasks_view(pilot)

        expected = [tasks, lxc, qemu, nodes, tasks]
        for expected_widget in expected:
            await pilot.press("tab")
            await pilot.pause()
            assert app.focused is expected_widget

        # focusing the left tables keeps switching the details pane to their mode
        assert details.current == "node_tasks_widget"


async def test_tab_forward_cycle_without_tasks_displayed(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        qemu = app.screen.query_one(QemuWidget)
        tasks = app.screen.query_one(NodeTasksWidget)
        details = app.screen.query_one(DetailsWidget)

        assert details.current == "node_summary_widget"

        expected = [lxc, qemu, nodes, lxc]
        for expected_widget in expected:
            await pilot.press("tab")
            await pilot.pause()
            assert app.focused is expected_widget
            assert app.focused is not tasks


async def test_shift_tab_reverse_cycle_with_tasks_displayed(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        qemu = app.screen.query_one(QemuWidget)
        details = app.screen.query_one(DetailsWidget)

        await show_tasks_view(pilot)

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is qemu

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is lxc

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is nodes
        assert details.current == "node_tasks_widget"


async def test_shift_tab_reverse_cycle_without_tasks_displayed(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        qemu = app.screen.query_one(QemuWidget)

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is qemu

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is lxc

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is nodes


async def test_shift_tab_from_lxc_with_tasks_displayed_reaches_task_list(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        tasks = app.screen.query_one(NodeTasksWidget)
        details = app.screen.query_one(DetailsWidget)

        await show_tasks_view(pilot)
        await pilot.press("tab")  # nodes -> task list
        await pilot.pause()
        await pilot.press("tab")  # task list -> LXC, details switches to LXC summary
        await pilot.pause()
        assert app.focused is lxc
        assert details.current == "lxc_summary_widget"

        # focus LXC while the Tasks view would still be displayed
        details.current = "node_tasks_widget"
        await pilot.pause()

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is tasks


async def test_shift_tab_from_task_list_reaches_nodes(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is nodes


async def test_arrow_keys_move_task_selection_and_keep_focus(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        tasks.move_cursor(row=0)
        await pilot.pause()

        await pilot.press("down")
        await pilot.pause()
        assert tasks.cursor_row == 1
        assert app.focused is tasks

        await pilot.press("up")
        await pilot.pause()
        assert tasks.cursor_row == 0
        assert app.focused is tasks


async def test_exactly_one_focused_pane(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        nodes = await focus_nodes_table(app, pilot)
        lxc = app.screen.query_one(LxcWidget)
        qemu = app.screen.query_one(QemuWidget)
        tasks = app.screen.query_one(NodeTasksWidget)
        details_pane = app.screen.query_one(DetailsWidget).parent

        await show_tasks_view(pilot)

        # the task list has no border of its own: its focus is shown on the details pane border
        app.screen.set_focus(tasks)
        await pilot.pause()
        assert details_pane.has_class("focused")
        assert not tasks.has_class("focused")
        assert not tasks.has_class("unfocused")
        assert not tasks.styles.border
        for table in (nodes, lxc, qemu):
            assert not table.has_class("focused")
        focused_widgets = app.screen.query(".focused")
        assert len(focused_widgets) == 1
        assert focused_widgets.first() is details_pane

        # the left tables keep their own focus border and clear the details pane
        for table in (nodes, lxc, qemu):
            app.screen.set_focus(table)
            await pilot.pause()
            assert table.has_class("focused")
            assert not details_pane.has_class("focused")
            assert not tasks.has_class("focused")
            for other in (nodes, lxc, qemu):
                if other is not table:
                    assert not other.has_class("focused")
            focused_widgets = app.screen.query(".focused")
            assert len(focused_widgets) == 1
            assert focused_widgets.first() is table


async def test_task_list_refreshes_while_focused(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks
        assert tasks.get_row_at(0)[5] == "OK"

        updated_tasks = [dict(TASKS[0], status="stopped"), dict(TASKS[1])]
        ProxmoxData.p_prox_resources["cluster/tasks"] = updated_tasks
        app.handle_update_message(app.NodesUpdated({"success": True, "text": "ok"}))
        await pilot.pause()

        assert tasks.get_row_at(0)[5] == "stopped"


async def test_unchanged_refresh_keeps_task_cursor(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        tasks.move_cursor(row=1)
        await pilot.pause()
        assert tasks.cursor_row == 1

        app.handle_update_message(app.NodesUpdated({"success": True, "text": "ok"}))
        await pilot.pause()

        assert tasks.cursor_row == 1


async def test_hidden_task_list_is_never_focused(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)
        details = app.screen.query_one(DetailsWidget)

        await show_tasks_view(pilot)
        assert details.current == "node_tasks_widget"

        # rotate node details from tasks to summary so the task list is hidden
        await pilot.press("d")
        await pilot.pause()
        assert details.current == "node_summary_widget"

        for _ in range(6):
            await pilot.press("tab")
            await pilot.pause()
            assert app.focused is not tasks

        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is not tasks


async def test_focused_task_list_keeps_details_layout(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)
        details = app.screen.query_one(DetailsWidget)

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        # the task list has no border of its own and the details pane shows its focus
        assert not tasks.styles.border
        assert details.parent.has_class("focused")

        right_column_region = details.parent.region
        assert tasks.row_count == 2
        assert right_column_region.x <= tasks.region.x
        assert right_column_region.y <= tasks.region.y
        assert tasks.region.right <= right_column_region.right
        assert tasks.region.bottom <= right_column_region.bottom
        assert tasks.content_region.height >= tasks.row_count


async def test_filter_from_task_list_opens_and_filters_tasks(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)
        details_pane = app.screen.query_one(DetailsWidget).parent

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks
        assert tasks.row_count == 2
        # the details pane border shows the view name and carries the focus state
        assert details_pane.border_title == "Tasks"
        assert details_pane.has_class("focused")
        assert not tasks.styles.border

        await open_filter_dialog(pilot)

        await pilot.press(*"Backup")
        await pilot.pause()
        assert app.screen.query_one("#input_filter", Input).value == "Backup"
        await pilot.press("enter")
        await pilot.pause()

        assert not isinstance(app.screen, FilterScreen)
        assert app.focused is tasks
        assert tasks.row_count == 1
        assert "Backup job" in tasks.get_row_at(0)
        assert details_pane.border_title == "Tasks (F)"


async def test_filter_cleared_from_task_list_restores_tasks(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)
        details_pane = app.screen.query_one(DetailsWidget).parent

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        await open_filter_dialog(pilot)
        await pilot.press(*"Backup")
        await pilot.press("enter")
        await pilot.pause()
        assert tasks.row_count == 1
        assert details_pane.border_title == "Tasks (F)"

        await open_filter_dialog(pilot)
        input_widget = app.screen.query_one("#input_filter", Input)
        assert input_widget.value == "Backup"
        input_widget.value = ""
        await pilot.press("enter")
        await pilot.pause()

        assert not isinstance(app.screen, FilterScreen)
        assert app.focused is tasks
        assert tasks.row_count == 2
        assert details_pane.border_title == "Tasks"


async def test_filter_survives_task_data_refresh(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)
        details_pane = app.screen.query_one(DetailsWidget).parent

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        await open_filter_dialog(pilot)
        await pilot.press(*"Backup")
        await pilot.press("enter")
        await pilot.pause()
        assert tasks.row_count == 1

        updated_tasks = [dict(TASKS[0], status="stopped"), dict(TASKS[1])]
        ProxmoxData.p_prox_resources["cluster/tasks"] = updated_tasks
        app.handle_update_message(app.NodesUpdated({"success": True, "text": "ok"}))
        await pilot.pause()

        assert tasks.row_count == 1
        assert "Backup job" in tasks.get_row_at(0)
        assert details_pane.border_title == "Tasks (F)"


async def test_filters_cleared_when_proxmox_reinitialized(seeded_proxmox):
    async with dashboard_app() as (app, pilot):
        await focus_nodes_table(app, pilot)
        tasks = app.screen.query_one(NodeTasksWidget)
        details_pane = app.screen.query_one(DetailsWidget).parent

        await show_tasks_view(pilot)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is tasks

        await open_filter_dialog(pilot)
        await pilot.press(*"Backup")
        await pilot.press("enter")
        await pilot.pause()
        assert tasks.filter_text == "Backup"
        assert tasks.row_count == 1
        assert details_pane.border_title == "Tasks (F)"

        # simulate a server change / Proxmox re-initialization without network or timers
        with (
            patch.object(app, "set_interval"),
            patch.object(app, "refresh_guests_data"),
        ):
            app.on_lazy_prox_proxmox_initialized(app.ProxmoxInitialized({"success": True, "text": "ok"}))
        await pilot.pause()

        assert tasks.filter_text == ""
        assert tasks.row_count == 2
        assert details_pane.border_title == "Tasks"
