"""Entry point for kpilot."""

from kpilot.config import Config
from kpilot.ui.app import KPilotApp


def main() -> None:
    config = Config.load()
    app = KPilotApp(config)
    app.run()


if __name__ == "__main__":
    main()
