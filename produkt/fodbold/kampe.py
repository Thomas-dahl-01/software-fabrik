"""Kampe: registrering og oversigt."""

from datetime import date

SPILLESTEDER = ("hjemme", "ude")


def opret_tabel(forbindelse):
    """Opret tabellen `kampe`, hvis den ikke findes."""
    forbindelse.execute(
        """
        CREATE TABLE IF NOT EXISTS kampe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dato TEXT NOT NULL,
            modstander TEXT NOT NULL,
            spillested TEXT NOT NULL CHECK (spillested IN ('hjemme', 'ude')),
            resultat TEXT NOT NULL
        )
        """
    )
    forbindelse.commit()


def registrer_kamp(forbindelse, dato, modstander, spillested, resultat):
    """Registrér en kamp og returnér den nye kamps id.

    `dato` skal være i ISO-format (fx "2026-11-23"), `spillested` skal være
    "hjemme" eller "ude", og `resultat` gemmes som tekst (fx "2-1").
    """
    try:
        date.fromisoformat(dato)
    except (TypeError, ValueError):
        raise ValueError("Datoen skal være i formatet ÅÅÅÅ-MM-DD.") from None
    if spillested not in SPILLESTEDER:
        raise ValueError("Spillested skal være 'hjemme' eller 'ude'.")
    markoer = forbindelse.execute(
        "INSERT INTO kampe (dato, modstander, spillested, resultat) "
        "VALUES (?, ?, ?, ?)",
        (dato, modstander, spillested, resultat),
    )
    forbindelse.commit()
    return markoer.lastrowid


def hent_kampe(forbindelse):
    """Returnér alle kampe som en liste af dicts, sorteret efter dato."""
    raekker = forbindelse.execute(
        "SELECT id, dato, modstander, spillested, resultat FROM kampe "
        "ORDER BY dato, id"
    ).fetchall()
    return [
        {
            "id": raekke[0],
            "dato": raekke[1],
            "modstander": raekke[2],
            "spillested": raekke[3],
            "resultat": raekke[4],
        }
        for raekke in raekker
    ]
