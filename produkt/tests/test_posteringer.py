"""Tests for datamodellen for posteringer."""

import sqlite3

import posteringer
from posteringer import hent_posteringer, tilføj_postering


def test_tilfoej_og_hent_postering(tmp_path):
    db = tmp_path / "finans.db"
    tilføj_postering("2026-11-01", 2500000, "Løn", "Indkomst", db_sti=db)
    tilføj_postering("2026-11-02", -12950, "Netto", "Mad", db_sti=db)

    assert hent_posteringer(db_sti=db) == [
        {"dato": "2026-11-01", "beløb": 2500000, "beskrivelse": "Løn", "kategori": "Indkomst"},
        {"dato": "2026-11-02", "beløb": -12950, "beskrivelse": "Netto", "kategori": "Mad"},
    ]


def test_hent_fra_tom_database(tmp_path):
    assert hent_posteringer(db_sti=tmp_path / "finans.db") == []


def test_beloeb_gemmes_som_heltal(tmp_path):
    db = tmp_path / "finans.db"
    tilføj_postering("2026-11-03", -4999, "Bog", "Fritid", db_sti=db)
    with sqlite3.connect(db) as forbindelse:
        (type_,) = forbindelse.execute("SELECT typeof(beløb) FROM posteringer").fetchone()
    assert type_ == "integer"


def test_tabellen_har_korrekte_kolonner(tmp_path):
    db = tmp_path / "finans.db"
    hent_posteringer(db_sti=db)  # opretter tabellen
    with sqlite3.connect(db) as forbindelse:
        kolonner = [
            (navn, type_)
            for _, navn, type_, *_ in forbindelse.execute("PRAGMA table_info(posteringer)")
        ]
    assert kolonner == [
        ("dato", "TEXT"),
        ("beløb", "INTEGER"),
        ("beskrivelse", "TEXT"),
        ("kategori", "TEXT"),
    ]


def test_standarddatabase_ligger_i_produkt_data():
    assert posteringer.STANDARD_DB.parts[-3:] == ("produkt", "data", "finans.db")


def test_standarddatabase_bruges_uden_sti(tmp_path, monkeypatch):
    db = tmp_path / "data" / "finans.db"
    monkeypatch.setattr(posteringer, "STANDARD_DB", db)
    tilføj_postering("2026-11-04", 100, "Test", "Andet")
    assert db.exists()
    assert len(hent_posteringer()) == 1
