import pytest

from fodbold import cli, db, spillere


@pytest.fixture
def forbindelse():
    forb = db.forbind(":memory:")
    yield forb
    forb.close()


def test_opret_spiller_via_cli(forbindelse, capsys):
    kode = cli.main(
        ["spiller", "opret", "--navn", "Anna Hansen", "--nummer", "10",
         "--position", "Angriber"],
        forbindelse=forbindelse,
    )

    assert kode == 0
    assert "Anna Hansen" in capsys.readouterr().out
    gemt = spillere.hent_spillere(forbindelse)
    assert len(gemt) == 1
    assert gemt[0]["troejenummer"] == 10
    assert isinstance(gemt[0]["troejenummer"], int)


def test_opret_spiller_via_cli_afviser_nummer_der_ikke_er_tal(forbindelse):
    with pytest.raises(SystemExit):
        cli.main(
            ["spiller", "opret", "--navn", "Anna", "--nummer", "ti",
             "--position", "Angriber"],
            forbindelse=forbindelse,
        )
    assert spillere.hent_spillere(forbindelse) == []


def test_liste_tom_database(forbindelse, capsys):
    cli.main(["spiller", "liste"], forbindelse=forbindelse)
    assert capsys.readouterr().out.strip() == "Ingen spillere på holdet."


def test_liste_viser_spillerens_information(forbindelse, capsys):
    spillere.opret_spiller(forbindelse, "Bo Jensen", 7, "Midtbane")

    cli.main(["spiller", "liste"], forbindelse=forbindelse)

    ud = capsys.readouterr().out
    linje = [l for l in ud.splitlines() if "Bo Jensen" in l][0]
    assert "7" in linje
    assert "Midtbane" in linje


def test_forbind_bruger_fodbold_db(tmp_path, monkeypatch):
    sti = tmp_path / "test.db"
    monkeypatch.setenv("FODBOLD_DB", str(sti))
    forb = db.forbind()
    spillere.opret_spiller(forb, "Anna", 9, "Angriber")
    forb.close()
    assert sti.exists()
