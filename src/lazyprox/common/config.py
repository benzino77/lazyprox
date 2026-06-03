import os
import tomllib as toml
from typing import List, Optional

from pydantic import BaseModel
from pathlib import Path


class ProxmoxServerConfig(BaseModel):
    name: str
    host: str
    user: str
    realm: str
    token_name: str
    token_value: str
    verify_ssl: Optional[bool] = True  # default to True


class ApplicationConfig(BaseModel):
    refresh_interval: Optional[float] = 10.0
    refresh_interval_rrddata: Optional[float] = 30.0
    refresh_interval_tasks: Optional[float] = 15.0
    debug_dump_dest: Optional[str] = "lazyprox-dump.json"
    rrddata_timeframe: Optional[str] = "hour"  # timeframe for rrd data
    rrddata_cf: Optional[str] = "AVERAGE"  # consolidation function


class ConfigDict(BaseModel):
    server: List[ProxmoxServerConfig]
    # use default values if missing
    application: Optional[ApplicationConfig] = ApplicationConfig()


class _Config():
    configuration: ConfigDict = None
    server_index: int = 0

    def load_config(self, config_file_path: str | None = None, server_index: int = 0) -> None:
        self.server_index = server_index

        if not config_file_path:
            # I'm not sure MacOS has this env variable
            cfg_f = Path(os.getenv("XDG_CONFIG_HOME", Path.home() /
                         ".config")) / "lazyprox" / "config.toml"
        else:
            cfg_f = Path(config_file_path)

        with open(cfg_f, "rb") as f:
            cfg = toml.load(f)
            # validate the configuration file
            self.configuration = ConfigDict(**cfg).model_dump()


Config = _Config()
