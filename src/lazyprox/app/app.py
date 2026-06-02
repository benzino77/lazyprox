import os
from typing import Literal
from itertools import product

from textual.app import App
from textual.message import Message
from textual.binding import Binding
from textual.timer import Timer
from textual import work
from textual.widgets import DataTable

from .resource_actions import ResourceActions
from lazyprox.common import Config
from lazyprox.data import ProxmoxData
from lazyprox.screens import WaitingScreen, ServerSelectionScreen, DashboardScreen, FilterScreen, ActionSelectionScreen
from lazyprox.widgets import NodeWidget, LxcWidget, QemuWidget


class LazyProx(App):
    BINDINGS = [
        Binding("D", "dump_debug", "Dump debug", show=False),
        ("f", "filter", "Filter"),
        ("s", "change_server", "Change server"),
        ("q", "quit", "Quit"),
    ]

    CSS_PATH = "styles.tcss"
    SCREENS = {"select_server": ServerSelectionScreen,
               "waiting": WaitingScreen,
               "dashboard": DashboardScreen}

    class _AppMessage(Message):
        def __init__(self, msg: dict | None = None):
            self.msg = msg or {}
            super().__init__()

    class ProxmoxInitialized(_AppMessage):
        """Sent when app starts or a server is selected."""

    class NodesUpdated(_AppMessage):
        """Sent when node data is refreshed."""

    class LxcsUpdated(_AppMessage):
        """Sent when LXC container data is refreshed."""

    class QemusUpdated(_AppMessage):
        """Sent when QEMU VM data is refreshed."""

    def __init__(self):
        self.timers: list[Timer] = []
        super().__init__()

    def handle_update_message(self, widget_name: str, msg: Message) -> None:
        """
        This is helper function to handle update message for nodes, lxcs and qemus widdgets
        Args:
            widget_name: name of the widget which should be updated
            msg: message which is send with update status
        Returns:
            None
        """
        success = msg.msg["success"]
        text = msg.msg["text"]
        if not success:
            self.notify(
                message=text, title="Something went wrong...", severity="error")
            return

        try:
            widget = self.screen.query_one(widget_name)
            widget.update_table_data()
        except Exception:
            return

    def stop_timers(self) -> None:
        for timer in self.timers:
            timer.stop()
        self.timers = []

    async def select_server(self) -> None:
        Config.server_index = await self.push_screen_wait("select_server")
        self.push_screen("waiting")

    def refresh_basic_nodes_data(self) -> None:
        ProxmoxData.refresh_api_information("nodes")
        nodes = ProxmoxData.p_prox_resources.get("nodes", [])
        for node in nodes:
            node_name: str = node["node"]
            ProxmoxData.refresh_api_information(f"nodes/{node_name}/status")
            ProxmoxData.refresh_api_information(f"nodes/{node_name}/qemu")
            ProxmoxData.refresh_api_information(f"nodes/{node_name}/lxc")

    def refresh_rrd_nodes_data(self) -> None:
        nodes = ProxmoxData.p_prox_resources.get("nodes", [])
        for node in nodes:
            node_name: str = node["node"]
            ProxmoxData.refresh_api_information(f"nodes/{node_name}/rrddata")

    @work(thread=True)
    def refresh_nodes_data(self, data_type: Literal["basic", "rrddata"]) -> None:
        try:
            if data_type == "basic":
                self.refresh_basic_nodes_data()
            if data_type == "rrddata":
                self.refresh_rrd_nodes_data()
            msg = self.NodesUpdated(
                {"success": True, "text": "Nodes data updated successfully"})
        except Exception as e:
            msg = self.NodesUpdated({"success": False, "text": str(e)})
        finally:
            self.post_message(msg)

    @work(thread=True)
    def refresh_guests_data(self, data_type: Literal["basic", "rrddata"], guest_type: Literal["qemu", "lxc"]) -> None:
        guests = ProxmoxData.get_guests_list(guest_type)
        path_suffix = {
            "basic": "status/current",
            "rrddata": "rrddata",
        }[data_type]

        msg_cls = {
            "lxc": self.LxcsUpdated,
            "qemu": self.QemusUpdated,
        }[guest_type]

        try:
            for g in guests:
                url = f"nodes/{g['node']}/{guest_type}/{g['vmid']}/{path_suffix}"
                ProxmoxData.refresh_api_information(url)

            msg = msg_cls(
                {"success": True,
                    "text": f"{guest_type.capitalize()} data updated successfully"}
            )
        except Exception as e:
            msg = msg_cls({"success": False, "text": str(e)})
        finally:
            self.post_message(msg)

    @work(thread=True)
    async def initialize_proxmox(self) -> None:
        """Initialize Proxmox and gets basic and rrd nodes information"""
        # The Proxmox needs to be initialized with new data
        # post_message is thread safe. That operation should not be blocking
        # because the "waiting screen" will not work
        # when finished message is sent with status
        try:
            ProxmoxData.initialize()
            self.refresh_basic_nodes_data()
            self.refresh_rrd_nodes_data()
            msg = self.ProxmoxInitialized(
                {"success": True, "text": "Proxmox initialized successfully"})
        except Exception as e:
            msg = self.ProxmoxInitialized({"success": False, "text": str(e)})
        finally:
            self.post_message(msg)

    @work()
    async def on_mount(self) -> None:
        self.stop_timers()
        await self.select_server()
        self.initialize_proxmox()

    def on_lazy_prox_proxmox_initialized(self, pim: ProxmoxInitialized) -> None:
        """
        Handler for ProxmoxInitialized message, this is called when Proxmox is initialized after server selection or application start
        It will start timers/intervals to refresh data (for nodes and guests) periodically.
        """
        self.switch_screen("dashboard")
        success = pim.msg["success"]
        text = pim.msg["text"]
        # something went wrong display popup with message
        if not success:
            self.notify(
                message=text, title="Something went wrong...", severity="error")
        else:
            # now we can start timers to update data in the background
            interval = Config.configuration.get(
                "application").get("refresh_interval")
            rrd_interval = Config.configuration.get(
                "application").get("refresh_interval_rrddata")
            self.timers.append(self.set_interval(interval, lambda:
                                                 self.refresh_nodes_data("basic")))
            self.timers.append(self.set_interval(rrd_interval, lambda:
                                                 self.refresh_nodes_data("rrddata")))

            # before starting intervals for guests lets get asynchronously their data
            # so it will be collected before timers collects data for the first time after interval
            # in other words we are doing it to avoid situation when the application is started and there is no data about guests
            # until the first interval is finished and data is collected for the first time
            # "product" function is used to produce pairs of type and guest for which we want to collect data,
            # so we will have pairs like ("basic", "lxc"), ("rrddata", "lxc"), ("basic", "qemu"), ("rrddata", "qemu")
            pairs = list(product(["basic", "rrddata"], ["lxc", "qemu"]))
            for data_type, guest_type in pairs:
                # collect data asap
                self.refresh_guests_data(data_type, guest_type)
                # then start intervals to collect data in the background
                self.timers.append(self.set_interval(interval if data_type == "basic" else rrd_interval,
                                   lambda t=data_type, g=guest_type: self.refresh_guests_data(t, g)))

        # update widgets if the data is available it will display gathered information
        # in other case the data in widgets will be cleared
        for widget_type in [NodeWidget, LxcWidget, QemuWidget]:
            try:
                widget = self.screen.query_one(widget_type)
                widget.filter_text = ""
                widget.remove_border_indicator("(F)")
                widget.update_table_data()
                widget.action_scroll_top()
                # set focus on the NodeWidget after Proxmox is initialized
                self.screen.set_focus(
                    widget) if widget_type is NodeWidget else None
            except Exception:
                continue

    def on_lazy_prox_nodes_updated(self, nu: NodesUpdated) -> None:
        self.handle_update_message("NodeWidget", nu)

    def on_lazy_prox_lxcs_updated(self, lu: LxcsUpdated) -> None:
        self.handle_update_message("LxcWidget", lu)

    def on_lazy_prox_qemus_updated(self, qu: QemusUpdated) -> None:
        self.handle_update_message("QemuWidget", qu)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # when "enter" is pressed on DataTable widget, the action screen should be displayed
        resource_actions = ResourceActions(event)
        list_items = resource_actions.get_actions_list()
        resource_name = resource_actions.get_resource_name()

        def check_action(selected_action: str | None) -> None:
            if selected_action == "SSH":
                with self.suspend():
                    os.system(f"ssh {resource_name}")
                self.app.refresh()
            else:
                try:
                    resource_actions.perform_action(selected_action)
                    self.notify(message=f"{selected_action} on {resource_name} successful", title="Action",
                                severity="information")
                except Exception as e:
                    self.notify(message=str(
                        e), title="Something went wrong...", severity="error")

        self.push_screen(ActionSelectionScreen(items=list_items), check_action)

    @work()
    async def action_change_server(self) -> None:
        self.stop_timers()
        await self.select_server()
        self.initialize_proxmox()

    def action_filter(self):
        # filter screen can only be displayed when dashboard screen is active
        if not isinstance(self.screen, DashboardScreen):
            return

        focused_widget = self.screen.query_one(".focused")

        def check_filter(text: str | None) -> None:
            # add indicator that data in the DataTable is filtered
            if text:
                focused_widget.add_border_indicator("(F)")
            else:
                focused_widget.remove_border_indicator("(F)")
            focused_widget.filter_text = text
            focused_widget.update_table_data()

        self.push_screen(FilterScreen(widget=focused_widget), check_filter)

    def action_dump_debug(self):
        try:
            path = ProxmoxData.dump_resources()
            self.notify(message=str(path), title="Dump file saved",
                        severity="information")
        except Exception as e:
            self.notify(message=str(
                e), title="Something went wrong...", severity="error")

    def action_quit(self) -> None:
        self.stop_timers()
        self.app.exit()
