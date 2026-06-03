from textual.widget import Widget


def set_focus_border(handler: Widget) -> None:
    """Function to set border on focused widget and remove border from all other widgets
    Args:
        handler: the widget for which the focus event was triggered
    Returns:
        None
    """
    # get all DataTable widgets
    data_table_widgets = handler.screen.query("LeftColumn DataTable")
    # set all widgets to class unfocused
    for widget in data_table_widgets:
        widget.remove_class("focused", "unfocused")
        widget.add_class("unfocused")

    # add class focused to the widget that triggered the event
    handler.remove_class("unfocused")
    handler.add_class("focused", update=True)


def calculate_uptime(uptime_seconds: int) -> str:
    """Calculate uptime in days, hours, minutes, and seconds from a given number of seconds.
    Args:
        uptime_seconds: The uptime in seconds.
    Returns:
        A string representing the uptime in the format "Xd Xh Xm Xs".
    """
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable units (B, KiB, MiB, GiB).
    Args:
        bytes_value: The value in bytes to format.
    Returns:
        A string representing the formatted byte value with appropriate units.
    """
    if bytes_value >= 1024**3:
        return f"{bytes_value / 1024**3:.2f} GiB"
    elif bytes_value >= 1024**2:
        return f"{bytes_value / 1024**2:.2f} MiB"
    elif bytes_value >= 1024:
        return f"{bytes_value / 1024:.2f} KiB"
    else:
        return f"{bytes_value} B"
