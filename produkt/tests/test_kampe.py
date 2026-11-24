import pytest

from fodbold import db, kampe


@pytest.fixture
def forbindelse():
    forb = db.forbind(":memory:")
    yield forb
    forb.close()


def test_registrer_kamp_gemmer_korrekte_data(forbindelse):
    kamp_id = kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")

    raekke = forbindelse.execute(
        "SELECT dato, modstander, spillested, resultat FROM kampe WHERE id = ?",
        (kamp_id,),
    ).fetchone()
    assert tuple(raekke) == ("2026-11-23", "Vejle B", "hjemme", "2-1")


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
        "resultat": "1-3",
    }
