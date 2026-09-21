import os
import tomllib as toml
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel
from textual.color import Color, ColorParseError

from .singleton import singleton


def _validate_color(value: str) -> str:
    try:
        Color.parse(value)
    except ColorParseError as e:
        raise ValueError(str(e)) from e
    return value


ColorString = Annotated[str, AfterValidator(_validate_color)]


class ProxmoxServerConfig(BaseModel):
    name: str
    host: str
    user: str
    realm: str
    token_name: str
    token_value: str
    verify_ssl: bool | None = True  # default to True


class ApplicationConfig(BaseModel):
    refresh_interval: float | None = 10.0
    refresh_interval_rrddata: float | None = 30.0
    refresh_interval_tasks: float | None = 15.0
    debug_dump_dest: str | None = "lazyprox-dump.json"
    rrddata_timeframe: str | None = "hour"  # timeframe for rrd data
    rrddata_cf: str | None = "AVERAGE"  # consolidation function


class ThemeConfig(BaseModel):
    primary: ColorString
    secondary: ColorString
    accent: ColorString
    warning: ColorString
    error: ColorString
    success: ColorString
    foreground: ColorString
    background: ColorString
    surface: ColorString
    panel: ColorString
    dark: bool = True


class ConfigDict(BaseModel):
    server: list[ProxmoxServerConfig]
    # use default values if missing
    application: ApplicationConfig | None = ApplicationConfig()
    theme: ThemeConfig | None = None


@singleton
class _Config:
    configuration: ConfigDict = None
    server_index: int = 0

    def load_config(self, config_file_path: str | None = None, server_index: int = 0) -> None:
        self.server_index = server_index

        if not config_file_path:
            # I'm not sure MacOS has this env variable
            cfg_f = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "lazyprox" / "config.toml"
        else:
            cfg_f = Path(config_file_path)

        with open(cfg_f, "rb") as f:
            cfg = toml.load(f)
            # validate the configuration file
            self.configuration = ConfigDict(**cfg).model_dump()


Config = _Config()
