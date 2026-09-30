from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button, Select, SelectionList

from lazyprox.app.bulk import (
    BulkGuest,
    BulkNode,
    BulkState,
    BulkSubmission,
    Operation,
    confirmation_message,
    eligible_guests,
    online_node_names,
    row_prompt,
)


def _node_value(value: object) -> str | None:
    if value is None or value is Select.NULL or value is Select.BLANK:
        return None
    return str(value)


class BulkScreen(ModalScreen[BulkSubmission | None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("a", "toggle_all", "All"),
    ]

    def __init__(
        self,
        nodes: list[BulkNode],
        guests: list[BulkGuest],
        highlighted_node: str | None = None,
        state: BulkState | None = None,
    ) -> None:
        super().__init__()
        self.nodes = list(nodes)
        self.guests = list(guests)
        self.highlighted_node = highlighted_node
        if state is None:
            self._operation: Operation = "start"
            self._checked: set[tuple[str, int]] = set()
            self._source: str | None = None
            self._target: str | None = None
        else:
            self._operation = state.operation
            self._checked = set(state.checked)
            self._source = state.source
            self._target = state.target
        self._applied_operation = self._operation
        self._applied_source = self._source
        self._suppress = False

    def _operation_options(self) -> list[tuple[str, str]]:
        options = [("Start", "start"), ("Shutdown", "shutdown")]
        if len(online_node_names(self.nodes)) >= 2:
            options.append(("Migrate", "migrate"))
        return options

    def compose(self) -> ComposeResult:
        with Vertical(id="bulk_dialog"):
            yield Select(
                self._operation_options(),
                prompt="Operation",
                allow_blank=False,
                value=self._operation,
                id="bulk_operation",
                type_to_search=False,
            )
            yield SelectionList(id="bulk_guests")
            with Horizontal(id="bulk_buttons"):
                yield Button("Cancel", id="bulk_cancel")
                yield Button("Run", id="bulk_run", variant="primary", disabled=True)

    async def on_mount(self) -> None:
        if self._operation == "migrate":
            await self._mount_migrate(prefill=False)
        self._rebuild_guests()
        self._update_run()

    def _guest_list(self) -> SelectionList:
        return self.query_one("#bulk_guests", SelectionList)

    def _rebuild_guests(self) -> None:
        include_node = self._operation != "migrate"
        options = [
            (
                row_prompt(guest, include_node=include_node),
                (guest.guest_type, guest.vmid),
                (guest.guest_type, guest.vmid) in self._checked,
            )
            for guest in eligible_guests(self.guests, self._operation, self._source)
        ]
        guest_list = self._guest_list()
        guest_list.clear_options()
        if options:
            guest_list.add_options(options)

    def _update_run(self) -> None:
        enabled = bool(self._guest_list().selected)
        if self._operation == "migrate":
            enabled = enabled and self._target is not None
        self.query_one("#bulk_run", Button).disabled = not enabled

    async def _mount_migrate(self, *, prefill: bool) -> None:
        try:
            self.query_one("#bulk_migrate")
        except NoMatches:
            pass
        else:
            return
        online = online_node_names(self.nodes)
        if prefill:
            self._source = self.highlighted_node if self.highlighted_node in online else None
            self._target = None
        self._applied_source = self._source
        targets = [name for name in online if name != self._source]
        source = Select(
            [(name, name) for name in online],
            prompt="From",
            allow_blank=True,
            value=self._source if self._source is not None else Select.NULL,
            id="bulk_source",
            type_to_search=False,
        )
        target = Select(
            [(name, name) for name in targets],
            prompt="To",
            allow_blank=True,
            value=self._target if self._target is not None else Select.NULL,
            id="bulk_target",
            type_to_search=False,
        )
        self._suppress = True
        try:
            await self.mount(Horizontal(source, target, id="bulk_migrate"), before=self.query_one("#bulk_buttons"))
        finally:
            self._suppress = False

    async def _remove_migrate(self) -> None:
        try:
            row = self.query_one("#bulk_migrate")
        except NoMatches:
            self._source = None
            self._target = None
            self._applied_source = None
            return
        self._suppress = True
        try:
            await row.remove()
        finally:
            self._suppress = False
        self._source = None
        self._target = None
        self._applied_source = None

    async def _sync_target_options(self) -> None:
        targets = [name for name in online_node_names(self.nodes) if name != self._source]
        target = self.query_one("#bulk_target", Select)
        self._suppress = True
        try:
            target.set_options([(name, name) for name in targets])
            if self._target is not None:
                target.value = self._target
        finally:
            self._suppress = False

    async def _change_operation(self, operation: Operation) -> None:
        self._checked.clear()
        self._operation = operation
        self._applied_operation = operation
        if operation == "migrate":
            await self._mount_migrate(prefill=True)
        else:
            await self._remove_migrate()
        self._rebuild_guests()
        self._update_run()

    async def _change_source(self, value: object) -> None:
        self._source = _node_value(value)
        self._applied_source = self._source
        self._checked.clear()
        if self._target == self._source:
            self._target = None
        await self._sync_target_options()
        self._rebuild_guests()
        self._update_run()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if self._suppress:
            return
        if event.select.id == "bulk_operation":
            if event.value in (Select.NULL, Select.BLANK) or event.value == self._applied_operation:
                return
            await self._change_operation(event.value)
        elif event.select.id == "bulk_source":
            if _node_value(event.value) == self._applied_source:
                return
            await self._change_source(event.value)
        elif event.select.id == "bulk_target":
            self._target = _node_value(event.value)
            self._update_run()

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        self._checked = set(event.selection_list.selected)
        self._update_run()

    def action_toggle_all(self) -> None:
        guest_list = self._guest_list()
        if guest_list.option_count == 0:
            return
        if len(guest_list.selected) == guest_list.option_count:
            guest_list.deselect_all()
        else:
            guest_list.select_all()
        self._checked = set(guest_list.selected)
        self._update_run()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submission(self) -> BulkSubmission:
        selected = set(self._guest_list().selected)
        guests = tuple(
            guest
            for guest in eligible_guests(self.guests, self._operation, self._source)
            if (guest.guest_type, guest.vmid) in selected
        )
        return BulkSubmission(
            operation=self._operation,
            guests=guests,
            source=self._source,
            target=self._target,
            message=confirmation_message(self._operation, guests, self._source, self._target),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "bulk_cancel":
            self.dismiss(None)
        elif event.button.id == "bulk_run" and not event.button.disabled:
            self.dismiss(self._submission())
