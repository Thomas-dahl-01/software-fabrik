import pytest

from fodbold import db, spillere


@pytest.fixture
def forbindelse():
    forb = db.forbind(":memory:")
    yield forb
    forb.close()


def test_opret_spiller_gemmer_troejenummer_som_tal(forbindelse):
    spiller_id = spillere.opret_spiller(forbindelse, "Anna Hansen", 10, "Angriber")

    raekke = forbindelse.execute(
        "SELECT navn, troejenummer, typeof(troejenummer), position "
        "FROM spillere WHERE id = ?",
        (spiller_id,),
    ).fetchone()
    assert tuple(raekke) == ("Anna Hansen", 10, "integer", "Angriber")


def test_opret_spiller_afviser_troejenummer_som_tekst(forbindelse):
    with pytest.raises(TypeError):
        spillere.opret_spiller(forbindelse, "Anna Hansen", "10", "Angriber")
    assert spillere.hent_spillere(forbindelse) == []


def test_hent_spillere_tom_database(forbindelse):
    assert spillere.hent_spillere(forbindelse) == []


def test_hent_spillere_returnerer_korrekt_information(forbindelse):
    spillere.opret_spiller(forbindelse, "Bo Jensen", 7, "Midtbane")
    spillere.opret_spiller(forbindelse, "Carl Nielsen", 1, "Målmand")

    resultat = spillere.hent_spillere(forbindelse)

    assert [(s["navn"], s["troejenummer"], s["position"]) for s in resultat] == [
        ("Carl Nielsen", 1, "Målmand"),
        ("Bo Jensen", 7, "Midtbane"),
    ]
