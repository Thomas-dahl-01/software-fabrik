"""SQLite-forbindelse og oprettelse af tabeller."""

import os
import sqlite3
from pathlib import Path

from fodbold import kampe, spillere

STANDARD_STI = Path(__file__).resolve().parent.parent / "data" / "hold.db"


def forbind(sti=None):
    """Åbn databasen og sørg for, at alle tabeller findes.

    Stien vælges i denne rækkefølge: argumentet `sti`, miljøvariablen
    `FODBOLD_DB` og til sidst standardstien `produkt/data/hold.db`.
    """
    if sti is None:
        sti = os.environ.get("FODBOLD_DB") or STANDARD_STI
    if str(sti) != ":memory:":
        Path(sti).parent.mkdir(parents=True, exist_ok=True)
    forbindelse = sqlite3.connect(sti)
    forbindelse.row_factory = sqlite3.Row
    opret_tabeller(forbindelse)
    return forbindelse


def opret_tabeller(forbindelse):
    """Lad hvert modul oprette sine egne tabeller."""
    spillere.opret_tabel(forbindelse)
    kampe.opret_tabel(forbindelse)
