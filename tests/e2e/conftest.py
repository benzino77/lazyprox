import pytest

from lazyprox.common import Config

MULTI_SERVER_TOML = """\
[[server]]
name = "proxmox-alpha"
host = "192.168.1.10"
user = "root"
realm = "pam"
token_name = "test"
token_value = "secret-a"

[[server]]
name = "proxmox-beta"
host = "192.168.1.20"
user = "root"
realm = "pam"
token_name = "test"
token_value = "secret-b"
"""


@pytest.fixture(autouse=True)
def e2e_config(tmp_path):
    previous_configuration = Config.configuration
    previous_server_index = Config.server_index
    config_file = tmp_path / "config.toml"
    config_file.write_text(MULTI_SERVER_TOML)
    Config.load_config(config_file_path=str(config_file))
    yield
    Config.configuration = previous_configuration
    Config.server_index = previous_server_index


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.parent.name == "e2e":
            item.add_marker(pytest.mark.e2e)
