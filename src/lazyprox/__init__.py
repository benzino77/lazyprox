import argparse
import sys

from pydantic import ValidationError

from lazyprox.common import Config
from lazyprox.app import LazyProx


def main() -> None:
    parser = argparse.ArgumentParser(description="LazyProx Application")
    parser.add_argument("-c", "--config", type=str, required=False,
                        help="Path to the configuration file")
    args = parser.parse_args()
    try:
        Config.load_config(config_file_path=args.config)
    except ValidationError:
        print(f"Something went wrong when loading config file. Please check your configuration against the documentation.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Something went wrong: {e}", file=sys.stderr)
        sys.exit(2)

    app = LazyProx()
    app.run()
