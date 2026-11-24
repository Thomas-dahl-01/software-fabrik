import pytest

from fodbold import cli, db, kampe, spillere


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


def test_registrer_kamp_via_cli(forbindelse, capsys):
    kode = cli.main(
        ["kamp", "registrer", "--dato", "2026-11-23", "--modstander", "Vejle B",
         "--spillested", "hjemme", "--resultat", "2-1"],
        forbindelse=forbindelse,
    )

    assert kode == 0
    assert "Vejle B" in capsys.readouterr().out
    assert kampe.hent_kampe(forbindelse) == [
        {"id": 1, "dato": "2026-11-23", "modstander": "Vejle B",
         "spillested": "hjemme", "resultat": "2-1"}
    ]


def test_registrer_kamp_via_cli_afviser_ugyldigt_spillested(forbindelse):
    with pytest.raises(SystemExit):
        cli.main(
            ["kamp", "registrer", "--dato", "2026-11-23", "--modstander", "AGF",
             "--spillested", "neutral", "--resultat", "1-1"],
            forbindelse=forbindelse,
        )
    assert kampe.hent_kampe(forbindelse) == []


def test_registrer_kamp_via_cli_afviser_ugyldig_dato(forbindelse, capsys):
    kode = cli.main(
        ["kamp", "registrer", "--dato", "23-11-2026", "--modstander", "AGF",
         "--spillested", "ude", "--resultat", "1-1"],
        forbindelse=forbindelse,
    )

    assert kode == 1
    assert "Fejl" in capsys.readouterr().out
    assert kampe.hent_kampe(forbindelse) == []


def test_vis_kampe_tom_database(forbindelse, capsys):
    cli.vis_kampe(forbindelse)
    assert capsys.readouterr().out.strip() == "Ingen kampe registreret."


def test_vis_kampe_viser_alle_kampe(forbindelse, capsys):
    kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")
    kampe.registrer_kamp(forbindelse, "2026-12-01", "AGF", "ude", "1-3")

    cli.vis_kampe(forbindelse)

    ud = capsys.readouterr().out
    vejle = [l for l in ud.splitlines() if "Vejle B" in l][0]
    agf = [l for l in ud.splitlines() if "AGF" in l][0]
    assert "2026-11-23" in vejle and "hjemme" in vejle and "2-1" in vejle
    assert "2026-12-01" in agf and "ude" in agf and "1-3" in agf


def test_kamp_liste_via_cli(forbindelse, capsys):
    kampe.registrer_kamp(forbindelse, "2026-11-23", "Vejle B", "hjemme", "2-1")

    kode = cli.main(["kamp", "liste"], forbindelse=forbindelse)

    assert kode == 0
    assert "Vejle B" in capsys.readouterr().out
