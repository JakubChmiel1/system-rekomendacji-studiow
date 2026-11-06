"""Przygotowanie SQLite i uruchomienie aplikacji w kontenerze."""

import os
import sys

from app.database import initialize_database
from app.konta import zapewnij_konto_admina


if __name__ == "__main__":
    initialize_database()
    zapewnij_konto_admina()
    os.execv(sys.executable, [
        sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py",
        "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ])
