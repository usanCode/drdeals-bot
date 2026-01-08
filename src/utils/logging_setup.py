import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers (important on reload)
    while root.handlers:
        root.handlers.pop()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # 1) Console handler (PowerShell / Railway / Render)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # 2) Rolling file handler (daily)
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=logs_dir / "app.log",
        when="midnight",
        interval=1,
        backupCount=14,   # keep 14 days
        encoding="utf-8",
        utc=False,        # set True if you prefer UTC dates
    )

    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # 3) Activity log handler (daily rolling, separate file)
    activity_handler = TimedRotatingFileHandler(
        filename=logs_dir / "drdeals_bot_activity.log",
        when="midnight",
        interval=1,
        backupCount=14,   # keep 14 days
        encoding="utf-8",
        utc=True,         # activity timestamps are already UTC-based
    )

    activity_formatter = logging.Formatter(
        "%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    activity_handler.setLevel(logging.INFO)
    activity_handler.setFormatter(activity_formatter)

    activity_logger = logging.getLogger("activity")
    activity_logger.setLevel(logging.INFO)
    activity_logger.addHandler(activity_handler)
    activity_logger.propagate = False

    logging.captureWarnings(True)
