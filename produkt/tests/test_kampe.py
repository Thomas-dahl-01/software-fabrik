import sqlite3

import pytest

from fodbold import db, kampe


@pytest.fixture
def forbindelse():
    forb = db.forbind(":memory:")
    yield forb
    forb.close()


def test_registrer_kamp_gemmer_resultat_som_to_heltal(forbindelse):
    kamp_id = kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")

    raekke = forbindelse.execute(
        "SELECT dato, modstander, spillested, vores_maal, deres_maal "
        "FROM kampe WHERE id = ?",
        (kamp_id,),
    ).fetchone()
    assert tuple(raekke) == ("2026-11-23", "Vejle B", "hjemme", 2, 1)
    assert isinstance(raekke["vores_maal"], int)
    assert isinstance(raekke["deres_maal"], int)


def test_tabellen_har_ikke_kolonnen_resultat(forbindelse):
    kolonner = [r[1] for r in forbindelse.execute("PRAGMA table_info(kampe)")]
    assert "resultat" not in kolonner
    assert "vores_maal" in kolonner and "deres_maal" in kolonner


@pytest.mark.parametrize(
    "tekst, forventet",
    [("2-1", (2, 1)), ("0-0", (0, 0)), ("1-3", (1, 3)), ("10-12", (10, 12))],
)
def test_fortolk_resultat(tekst, forventet):
    assert kampe.fortolk_resultat(tekst) == forventet


@pytest.mark.parametrize(
    "resultat", ["abc", "2:1", "", "2-", "-1", "2-1-0", "-1-2", " 2-1", "2 - 1", "²-1", None]
)
def test_registrer_kamp_afviser_ugyldigt_resultat(forbindelse, resultat):
    with pytest.raises(ValueError, match="x-y"):
        kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", resultat)
    assert kampe.hent_kampe(forbindelse) == []


def test_samme_kamp_kan_ikke_registreres_to_gange(forbindelse):
    kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")

    with pytest.raises(ValueError, match="allerede registreret"):
        kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "ude", "0-3")

    liste = kampe.hent_kampe(forbindelse)
    assert len(liste) == 1
    assert (liste[0]["vores_maal"], liste[0]["deres_maal"]) == (2, 1)


def test_samme_modstander_paa_anden_dato_er_tilladt(forbindelse):
    kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")
    kampe.registrer_kamp(forbindelse, "2026-12-01", "Vejle B", "ude", "1-1")
    kampe.registrer_kamp(forbindelse, "2026-11-23", "AGF", "ude", "0-0")
    assert len(kampe.hent_kampe(forbindelse)) == 3


def test_kamp_findes(forbindelse):
    assert not kampe.kamp_findes(forbindelse, "2026-11-23", "Vejle B")
    kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")
    assert kampe.kamp_findes(forbindelse, "2026-11-23", "Vejle B")


def test_gammel_tabel_med_resultat_migreres(tmp_path):
    sti = tmp_path / "gammel.db"
    gammel = sqlite3.connect(sti)
    gammel.execute(
        "CREATE TABLE kampe (id INTEGER PRIMARY KEY AUTOINCREMENT, dato TEXT NOT NULL, "
        "modstander TEXT NOT NULL, spillested TEXT NOT NULL, resultat TEXT NOT NULL)"
    )
    gammel.execute(
        "INSERT INTO kampe (dato, modstander, spillested, resultat) "
        "VALUES ('2026-11-01', 'OB', 'ude', '1-1')"
    )
    gammel.commit()
    gammel.close()

    forb = db.forbind(sti)
    try:
        kolonner = [r[1] for r in forb.execute("PRAGMA table_info(kampe)")]
        assert "resultat" not in kolonner
        kampe.registrer_kamp(forb, "2026-11-23", "Vejle B", "hjemme", "2-1")
        assert len(kampe.hent_kampe(forb)) == 1
    finally:
        forb.close()


def test_formater_resultat():
    assert kampe.formater_resultat({"vores_maal": 2, "deres_maal": 1}) == "2-1"


def test_registrer_kamp_afviser_ukendt_spillested(forbindelse):
    with pytest.raises(ValueError):
        kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "neutral", "2-1")
    assert kampe.hent_kampe(forbindelse) == []


@pytest.mark.parametrize("dato", ["23-11-2026", "2026-13-01", "i morgen", None])
def test_registrer_kamp_afviser_ugyldig_dato(forbindelse, dato):
    with pytest.raises(ValueError):
        kampe.registrer_kamp(forbindelse, dato, "Vejle B", "ude", "0-0")
    assert kampe.hent_kampe(forbindelse) == []


def test_hent_kampe_tom_database(forbindelse):
    assert kampe.hent_kampe(forbindelse) == []


def test_hent_kampe_sorterer_efter_dato(forbindelse):
    kampe.registrer_kamp(forbindelse, "2026-12-01", "AGF", "ude", "1-3")
    kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")

    liste = kampe.hent_kampe(forbindelse)

    assert [k["modstander"] for k in liste] == ["Vejle B", "AGF"]
    assert liste[1] == {
        "id": 1,
        "dato": "2026-12-01",
        "modstander": "AGF",
        "spillested": "ude",
        "vores_maal": 1,
        "deres_maal": 3,
    }
