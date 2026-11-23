"""Datamodel og database for posteringer.

Beløb gemmes som heltal i øre. Indtægter er positive, udgifter negative.
"""

import sqlite3
from pathlib import Path

# Standardplacering af databasen: produkt/data/finans.db
STANDARD_DB = Path(__file__).resolve().parent / "data" / "finans.db"

_OPRET_TABEL = """
CREATE TABLE IF NOT EXISTS posteringer (
    dato TEXT,
    beløb INTEGER,
    beskrivelse TEXT,
    kategori TEXT
)
"""


def _forbind(db_sti: str | Path | None) -> sqlite3.Connection:
    """Åbn forbindelse til databasen og sørg for, at tabellen findes."""
    sti = Path(db_sti) if db_sti is not None else STANDARD_DB
    sti.parent.mkdir(parents=True, exist_ok=True)
    forbindelse = sqlite3.connect(sti)
    forbindelse.execute(_OPRET_TABEL)
    return forbindelse


def tilføj_postering(
    dato: str,
    beløb: int,
    beskrivelse: str,
    kategori: str,
    db_sti: str | Path | None = None,
) -> None:
    """Tilføj en postering. `beløb` er i øre (positiv = indtægt, negativ = udgift)."""
    forbindelse = _forbind(db_sti)
    try:
        with forbindelse:
            forbindelse.execute(
                "INSERT INTO posteringer (dato, beløb, beskrivelse, kategori) "
                "VALUES (?, ?, ?, ?)",
                (dato, beløb, beskrivelse, kategori),
            )
    finally:
        forbindelse.close()


def hent_posteringer(db_sti: str | Path | None = None) -> list[dict]:
    """Hent alle posteringer i den rækkefølge, de blev tilføjet."""
    forbindelse = _forbind(db_sti)
    try:
        rækker = forbindelse.execute(
            "SELECT dato, beløb, beskrivelse, kategori FROM posteringer ORDER BY rowid"
        ).fetchall()
    finally:
        forbindelse.close()
    return [
        {"dato": dato, "beløb": beløb, "beskrivelse": beskrivelse, "kategori": kategori}
        for dato, beløb, beskrivelse, kategori in rækker
    ]
