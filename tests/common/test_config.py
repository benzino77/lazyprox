from lazyprox.common.config import (
    ApplicationConfig,
    Config,
    ConfigDict,
    ProxmoxServerConfig,
    _Config,
)

VALID_SERVER = {
    "name": "proxmox1",
    "host": "192.168.1.100",
    "user": "root",
    "realm": "pam",
    "token_name": "test",
    "token_value": "secret",
}

VALID_TOML = """\
[[server]]
name = "proxmox1"
host = "192.168.1.100"
user = "root"
realm = "pam"
token_name = "test"
token_value = "secret"
"""


def test_proxmox_server_config_required_fields():
    cfg = ProxmoxServerConfig(**VALID_SERVER)
    assert cfg.name == "proxmox1"
    assert cfg.host == "192.168.1.100"
    assert cfg.user == "root"
    assert cfg.realm == "pam"
    assert cfg.token_name == "test"
    assert cfg.token_value == "secret"


def test_proxmox_server_config_verify_ssl_defaults_true():
    cfg = ProxmoxServerConfig(**VALID_SERVER)
    assert cfg.verify_ssl is True


def test_proxmox_server_config_verify_ssl_false_honored():
    cfg = ProxmoxServerConfig(**VALID_SERVER, verify_ssl=False)
    assert cfg.verify_ssl is False


def test_application_config_defaults():
    cfg = ApplicationConfig()
    assert cfg.refresh_interval == 10.0
    assert cfg.refresh_interval_rrddata == 30.0
    assert cfg.refresh_interval_tasks == 15.0
    assert cfg.debug_dump_dest == "lazyprox-dump.json"
    assert cfg.rrddata_timeframe == "hour"
    assert cfg.rrddata_cf == "AVERAGE"


def test_config_dict_application_defaults_when_only_server():
    cfg = ConfigDict(server=[ProxmoxServerConfig(**VALID_SERVER)])
    assert isinstance(cfg.application, ApplicationConfig)
    assert cfg.application.refresh_interval == 10.0


def test_config_dict_application_overrides_honored():
    cfg = ConfigDict(
        server=[ProxmoxServerConfig(**VALID_SERVER)],
        application=ApplicationConfig(refresh_interval=5.0, rrddata_cf="MAX"),
    )
    assert cfg.application.refresh_interval == 5.0
    assert cfg.application.rrddata_cf == "MAX"


def test_load_config_explicit_path(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(VALID_TOML)

    Config.load_config(config_file_path=str(config_file), server_index=2)

    assert Config.configuration is not None
    assert Config.server_index == 2
    assert len(Config.configuration["server"]) == 1
    assert Config.configuration["server"][0]["name"] == "proxmox1"


def test_load_config_fallback_xdg(tmp_path, monkeypatch):
    config_dir = tmp_path / "lazyprox"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(VALID_TOML)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    Config.load_config(config_file_path=None)

    assert Config.configuration is not None
    assert len(Config.configuration["server"]) == 1


def test_config_is_singleton_instance():
    assert Config is _Config()
