from unittest.mock import patch

import pytest
from textual.widgets import Button, Select, SelectionList

from lazyprox.app import LazyProx
from lazyprox.core.bulk import BulkSummary
from lazyprox.data import ProxmoxData
from lazyprox.screens import BulkScreen, ConfirmationScreen, DashboardScreen, ServerSelectionScreen
from lazyprox.widgets import LxcWidget, NodeWidget
from tests.e2e import make_app, wait_for_server_selection

pytestmark = pytest.mark.e2e

RESOURCES = {
    "nodes": [
        {"node": "pve1", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
        {"node": "pve2", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
    ],
    "nodes/pve1/status": {},
    "nodes/pve2/status": {},
    "nodes/pve1/lxc": [],
    "nodes/pve1/qemu": [{"vmid": 100, "name": "db", "status": "stopped", "template": 0}],
    "nodes/pve2/lxc": [],
    "nodes/pve2/qemu": [{"vmid": 200, "name": "app", "status": "running", "template": 0}],
}

RUNNING_ONLY_RESOURCES = {
    "nodes": [
        {"node": "pve1", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
        {"node": "pve2", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1},
    ],
    "nodes/pve1/status": {},
    "nodes/pve2/status": {},
    "nodes/pve1/lxc": [],
    "nodes/pve1/qemu": [{"vmid": 100, "name": "db", "status": "running", "template": 0}],
    "nodes/pve2/lxc": [],
    "nodes/pve2/qemu": [],
}

NO_BULK_RESOURCES = {
    "nodes": [{"node": "pve1", "status": "online", "mem": 1, "maxmem": 2, "cpu": 0.1}],
    "nodes/pve1/status": {},
    "nodes/pve1/lxc": [],
    "nodes/pve1/qemu": [
        {"vmid": 100, "name": "db", "status": "stopped", "template": 1},
        {"vmid": 101, "name": "app", "status": "paused", "template": 0},
    ],
}


def dashboard_mount(self) -> None:
    self.push_screen("dashboard")


@pytest.fixture
def seeded_proxmox():
    previous = ProxmoxData.p_prox_resources
    ProxmoxData.p_prox_resources = RESOURCES
    yield
    ProxmoxData.p_prox_resources = previous


@pytest.fixture
def seeded_running_only():
    previous = ProxmoxData.p_prox_resources
    ProxmoxData.p_prox_resources = RUNNING_ONLY_RESOURCES
    yield
    ProxmoxData.p_prox_resources = previous


@pytest.fixture
def seeded_no_bulk():
    previous = ProxmoxData.p_prox_resources
    ProxmoxData.p_prox_resources = NO_BULK_RESOURCES
    yield
    ProxmoxData.p_prox_resources = previous


async def wait_for_type(pilot, screen_type):
    for _ in range(50):
        if isinstance(pilot.app.screen, screen_type):
            await pilot.pause()
            return
        await pilot.pause()
    raise AssertionError(f"Expected {screen_type.__name__}, got {type(pilot.app.screen).__name__}")


async def test_b_does_not_open_bulk_on_server_selection():
    app = make_app()
    async with app.run_test() as pilot:
        await wait_for_server_selection(pilot)
        await pilot.press("b")
        await pilot.pause()
        app.action_bulk()
        await pilot.pause()
        assert isinstance(app.screen, ServerSelectionScreen)
        assert not any(isinstance(screen, BulkScreen) for screen in app.screen_stack)


async def test_no_bulk_operation_notifies_and_keeps_dashboard(seeded_no_bulk):
    app = LazyProx()
    with (
        patch.object(LazyProx, "on_mount", dashboard_mount),
        patch.object(app, "notify") as notify,
    ):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            await pilot.press("b")
            for _ in range(50):
                if any(
                    call.kwargs.get("message") == "No bulk operation is available" for call in notify.call_args_list
                ):
                    break
                await pilot.pause()
            else:
                raise AssertionError("Expected a no-operation notification")

            assert not any(isinstance(screen, BulkScreen) for screen in app.screen_stack)
            assert isinstance(app.screen, DashboardScreen)


async def test_no_reopens_bulk_with_operation_checks_source_and_target(seeded_running_only):
    app = LazyProx()
    with (
        patch.object(LazyProx, "on_mount", dashboard_mount),
        patch("lazyprox.app.app.dispatch_bulk") as dispatch,
    ):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            await pilot.press("b")
            await wait_for_type(pilot, BulkScreen)

            operation = app.screen.query_one("#bulk_operation", Select)
            assert [value for _, value in operation._options] == ["shutdown", "migrate"]
            assert operation.value == "shutdown"

            operation.value = "migrate"
            await pilot.pause()
            app.screen.query_one("#bulk_source", Select).value = "pve1"
            await pilot.pause()
            app.screen.query_one("#bulk_guests", SelectionList).select(("qemu", 100))
            await pilot.pause()
            app.screen.query_one("#bulk_target", Select).value = "pve2"
            await pilot.pause()
            await pilot.click("#bulk_run")
            await wait_for_type(pilot, ConfirmationScreen)

            assert app.screen.question == "Migrate 1 guest from pve1 to pve2 (1 VM)?"
            await pilot.click("#confirm_no")
            await wait_for_type(pilot, BulkScreen)

            assert app.screen.query_one("#bulk_operation", Select).value == "migrate"
            assert app.screen.query_one("#bulk_source", Select).value == "pve1"
            assert app.screen.query_one("#bulk_target", Select).value == "pve2"
            assert ("qemu", 100) in app.screen.query_one("#bulk_guests", SelectionList).selected
            dispatch.assert_not_called()


async def test_yes_dispatches_and_notifies(seeded_proxmox):
    app = LazyProx()
    summary = BulkSummary(operation="start", requested=1, failed=0)
    with (
        patch.object(LazyProx, "on_mount", dashboard_mount),
        patch("lazyprox.app.app.dispatch_bulk", return_value=summary) as dispatch,
        patch.object(app, "notify") as notify,
    ):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            await pilot.press("b")
            await wait_for_type(pilot, BulkScreen)
            app.screen.query_one("#bulk_guests", SelectionList).select(("qemu", 100))
            await pilot.pause()
            assert not app.screen.query_one("#bulk_run", Button).disabled
            await pilot.click("#bulk_run")
            await wait_for_type(pilot, ConfirmationScreen)
            assert app.screen.question == "Start 1 guest (1 VM)?"
            await pilot.click("#confirm_yes")
            for _ in range(50):
                if isinstance(app.screen, DashboardScreen) and dispatch.called and notify.called:
                    break
                await pilot.pause()
            else:
                raise AssertionError("Yes path did not dispatch and return to the dashboard")

            guests, operation = dispatch.call_args.args
            assert operation == "start"
            assert [guest.vmid for guest in guests] == [100]
            assert dispatch.call_args.kwargs["target"] is None
            assert notify.call_args.kwargs["message"] == "Start requested for 1 guest"
            assert "have shut down" not in notify.call_args.kwargs["message"]
            assert isinstance(app.screen, DashboardScreen)


async def test_migrate_source_prefills_from_nodes_cursor_when_another_table_is_focused(seeded_proxmox):
    app = LazyProx()
    with patch.object(LazyProx, "on_mount", dashboard_mount):
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_for_type(pilot, DashboardScreen)
            node_widget = app.screen.query_one(NodeWidget)
            node_widget.update_table_data()
            node_widget.move_cursor(row=0)
            app.screen.set_focus(app.screen.query_one(LxcWidget))
            await pilot.pause()
            assert not node_widget.has_focus

            await pilot.press("b")
            await wait_for_type(pilot, BulkScreen)
            app.screen.query_one("#bulk_operation", Select).value = "migrate"
            await pilot.pause()
            assert app.screen.query_one("#bulk_source", Select).value == "pve1"
