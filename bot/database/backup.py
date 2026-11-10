
import sqlite3

from datetime import datetime
from pathlib import Path

from bot.config import DB_PATH


BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = BASE_DIR / "backups"


def create_backup() -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime(
    "%Y-%m-%d_%H-%M-%S-%f"
)

    backup_path = BACKUP_DIR / f"applications_{timestamp}.db"

    with sqlite3.connect(DB_PATH) as source:
        with sqlite3.connect(backup_path) as destination:
            source.backup(destination)

    return backup_path
