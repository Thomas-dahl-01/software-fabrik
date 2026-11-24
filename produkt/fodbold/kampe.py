"""Kampe: registrering og oversigt."""

import re
from datetime import date

SPILLESTEDER = ("hjemme", "ude")

# Resultatet skrives som "x-y", hvor x er vores mål og y er deres mål.
RESULTAT_MOENSTER = re.compile(r"([0-9]+)-([0-9]+)")


def opret_tabel(forbindelse):
    """Opret tabellen `kampe`, hvis den ikke findes.

    Findes tabellen i det gamle format med tekstkolonnen `resultat`, slettes
    den og oprettes på ny (eksisterende kampe må gerne slettes ved migrering).
    """
    kolonner = [
        raekke[1]
        for raekke in forbindelse.execute("PRAGMA table_info(kampe)").fetchall()
    ]
    if "resultat" in kolonner:
        forbindelse.execute("DROP TABLE kampe")
    forbindelse.execute(
        """
        CREATE TABLE IF NOT EXISTS kampe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dato TEXT NOT NULL,
            modstander TEXT NOT NULL,
            spillested TEXT NOT NULL CHECK (spillested IN ('hjemme', 'ude')),
            vores_maal INTEGER NOT NULL CHECK (vores_maal >= 0),
            deres_maal INTEGER NOT NULL CHECK (deres_maal >= 0),
            UNIQUE (dato, modstander)
        )
        """
    )
    forbindelse.commit()


def fortolk_resultat(resultat):
    """Lav en resultattekst som "2-1" om til (vores_maal, deres_maal).

    Rejser ValueError, hvis teksten ikke har formatet "x-y" med heltal >= 0.
    """
    match = None
    if isinstance(resultat, str):
        match = RESULTAT_MOENSTER.fullmatch(resultat)
    if match is None:
        raise ValueError(
            "Resultatet skal være i formatet x-y, fx 2-1 (vores mål først)."
        )
    return int(match.group(1)), int(match.group(2))


def kamp_findes(forbindelse, dato, modstander):
    """Returnér True, hvis en kamp med samme dato og modstander er registreret."""
    raekke = forbindelse.execute(
        "SELECT 1 FROM kampe WHERE dato = ? AND modstander = ?",
        (dato, modstander),
    ).fetchone()
    return raekke is not None


def registrer_kamp(forbindelse, dato, modstander, spillested, resultat):
    """Registrér en kamp og returnér den nye kamps id.

    `dato` skal være i ISO-format (fx "2026-11-23"), `spillested` skal være
    "hjemme" eller "ude", og `resultat` skal være i formatet "x-y" (fx "2-1"),
    hvor første tal er vores mål. Resultatet gemmes som to heltal.
    Den samme kamp (dato og modstander) kan ikke registreres to gange.
    """
    try:
        date.fromisoformat(dato)
    except (TypeError, ValueError):
        raise ValueError("Datoen skal være i formatet ÅÅÅÅ-MM-DD.") from None
    if spillested not in SPILLESTEDER:
        raise ValueError("Spillested skal være 'hjemme' eller 'ude'.")
    vores_maal, deres_maal = fortolk_resultat(resultat)
    if kamp_findes(forbindelse, dato, modstander):
        raise ValueError(
            f"Kampen mod {modstander} den {dato} er allerede registreret."
        )
    markoer = forbindelse.execute(
        "INSERT INTO kampe (dato, modstander, spillested, vores_maal, deres_maal) "
        "VALUES (?, ?, ?, ?, ?)",
        (dato, modstander, spillested, vores_maal, deres_maal),
    )
    forbindelse.commit()
    return markoer.lastrowid


def formater_resultat(kamp):
    """Returnér kampens resultat som tekst, fx "2-1" (vores mål først)."""
    return f"{kamp['vores_maal']}-{kamp['deres_maal']}"


def hent_kampe(forbindelse):
    """Returnér alle kampe som en liste af dicts, sorteret efter dato."""
    raekker = forbindelse.execute(
        "SELECT id, dato, modstander, spillested, vores_maal, deres_maal "
        "FROM kampe ORDER BY dato, id"
    ).fetchall()
    return [
        {
            "id": raekke[0],
            "dato": raekke[1],
            "modstander": raekke[2],
            "spillested": raekke[3],
            "vores_maal": raekke[4],
            "deres_maal": raekke[5],
        }
        for raekke in raekker
    ]
