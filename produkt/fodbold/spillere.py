"""Spillere på holdet: oprettelse og oversigt."""


def opret_tabel(forbindelse):
    """Opret tabellen `spillere`, hvis den ikke findes."""
    forbindelse.execute(
        """
        CREATE TABLE IF NOT EXISTS spillere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            navn TEXT NOT NULL,
            troejenummer INTEGER NOT NULL,
            position TEXT NOT NULL
        )
        """
    )
    forbindelse.commit()


def opret_spiller(forbindelse, navn, troejenummer, position):
    """Opret en spiller og returnér den nye spillers id.

    Trøjenummeret skal være et heltal og gemmes som tal i databasen.
    """
    if isinstance(troejenummer, bool) or not isinstance(troejenummer, int):
        raise TypeError("Trøjenummeret skal være et heltal.")
    markoer = forbindelse.execute(
        "INSERT INTO spillere (navn, troejenummer, position) VALUES (?, ?, ?)",
        (navn, troejenummer, position),
    )
    forbindelse.commit()
    return markoer.lastrowid


def hent_spillere(forbindelse):
    """Returnér alle spillere som en liste af dicts, sorteret efter trøjenummer."""
    raekker = forbindelse.execute(
        "SELECT id, navn, troejenummer, position FROM spillere "
        "ORDER BY troejenummer, id"
    ).fetchall()
    return [
        {
            "id": raekke[0],
            "navn": raekke[1],
            "troejenummer": raekke[2],
            "position": raekke[3],
        }
        for raekke in raekker
    ]
