"""Tests af runneren med en falsk kodeagent og et lokalt "GitHub"-repo (bare repo).

Kør:  python -m pytest tests
"""

import json
import os
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runner"))
os.environ.setdefault("FABRIK_TOKEN", "test-token")
import runner  # noqa: E402

FALSK_AGENT = textwrap.dedent(r'''
    import json, os, sys, time
    prompt = sys.stdin.read()
    mode = os.environ["FALSK_MODE"]
    if mode == "sov":
        time.sleep(30)
    if mode in ("faerdig", "hemmelighed"):
        open("ny_fil.py", "w").write("print('hej')\n")
    if mode == "hemmelighed":
        open(".env", "w").write("NOEGLE=hemmelig\n")
    status = {"faerdig": "faerdig", "hemmelighed": "faerdig", "spoergsmaal": "spoergsmaal",
              "tom": "faerdig"}.get(mode)
    tekst = "Arbejdet er gjort."
    if status:
        blok = {"status": status, "opsummering": "lavede ny_fil.py", "tests": "1 passed",
                "spoergsmaal": "Skal beløb være i øre?" if status == "spoergsmaal" else ""}
        tekst += "\n```fabrik-status\n" + json.dumps(blok, ensure_ascii=False) + "\n```"
    assert "issue-7" in prompt and "Lav en fil" in prompt
    print(json.dumps({"type": "result", "result": tekst, "total_cost_usd": 0.12, "num_turns": 3}))
''')


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def opsaetning(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", str(remote), str(seed))
    (seed / "README.md").write_text("hej\n")
    git(seed, "add", "-A")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "start")
    git(seed, "push", "origin", "HEAD:main")

    agent = tmp_path / "falsk_agent.py"
    agent.write_text(FALSK_AGENT, encoding="utf-8")
    monkeypatch.setenv("PYTHONUTF8", "1")
    monkeypatch.setattr(runner, "REPO_URL", str(remote))
    monkeypatch.setattr(runner, "ARBEJDE", tmp_path / "arbejde")
    monkeypatch.setattr(runner, "REPO", tmp_path / "arbejde" / "repo")
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner, "TILSTAND_FIL", tmp_path / "tilstand.json")
    monkeypatch.setattr(runner, "agent_kommando", lambda: [sys.executable, str(agent)])
    monkeypatch.setattr(runner, "tilstand", {"aktiv": None, "resultater": {}})
    monkeypatch.setenv("GIT_AUTHOR_NAME", "agent")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "agent@fabrik")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "agent")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "agent@fabrik")
    return remote


def koer(monkeypatch, mode):
    monkeypatch.setenv("FALSK_MODE", mode)
    runner.tilstand["aktiv"] = {"issue": 7}
    runner.koer_opgave(7, "Lav en fil", "Lav en fil der hedder ny_fil.py")
    return runner.tilstand["resultater"]["7"]


def remote_branches(remote):
    return subprocess.run(["git", "branch", "--list"], cwd=remote, capture_output=True, text=True).stdout


def test_faerdig_pusher_branch(opsaetning, monkeypatch):
    res = koer(monkeypatch, "faerdig")
    assert res["status"] == "faerdig"
    assert res["commits"] == 1 and res["filer"] == ["ny_fil.py"]
    assert res["pris_usd"] == 0.12 and res["tests"] == "1 passed"
    assert "issue-7" in remote_branches(opsaetning)
    assert runner.tilstand["aktiv"] is None


def test_spoergsmaal(opsaetning, monkeypatch):
    res = koer(monkeypatch, "spoergsmaal")
    assert res["status"] == "spoergsmaal"
    assert "øre" in res["spoergsmaal"]


def test_uden_statusblok_sidder_fast(opsaetning, monkeypatch):
    assert koer(monkeypatch, "uden_status")["status"] == "sidder_fast"


def test_faerdig_uden_aendringer_sidder_fast(opsaetning, monkeypatch):
    res = koer(monkeypatch, "tom")
    assert res["status"] == "sidder_fast" and "ingen ændringer" in res["opsummering"]


def test_timeout_sidder_fast(opsaetning, monkeypatch):
    monkeypatch.setattr(runner, "TIMEOUT_SEK", 2)
    res = koer(monkeypatch, "sov")
    assert res["status"] == "sidder_fast" and "stoppet" in res["opsummering"]


def test_hemmelighed_pushes_ikke(opsaetning, monkeypatch):
    res = koer(monkeypatch, "hemmelighed")
    assert res["status"] == "sidder_fast" and "følsomme filer" in res["opsummering"]
    assert "issue-7" not in remote_branches(opsaetning)


def test_agent_fejl_vises_i_opsummering(opsaetning, monkeypatch):
    svar = json.dumps({"type": "result", "is_error": True, "result": "Not logged in · Please run /login"})
    monkeypatch.setattr(runner, "agent_kommando",
                        lambda: [sys.executable, "-c", f"import sys; sys.stdin.read(); print({svar!r})"])
    res = koer(monkeypatch, "faerdig")
    assert res["status"] == "sidder_fast" and "Not logged in" in res["opsummering"]


def test_statusblok_fortolkes():
    tekst = 'bla\n```fabrik-status\n{"status": "Færdig", "opsummering": "x"}\n```'
    assert runner.fortolk_status(tekst)["status"] == "faerdig"
    assert runner.fortolk_status("ingen blok") is None
    assert runner.fortolk_status('```fabrik-status\n{"status": "måske"}\n```') is None


def test_http_kraever_token(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "TOKEN", "hemmelig")
    monkeypatch.setattr(runner, "TILSTAND_FIL", tmp_path / "t.json")
    monkeypatch.setattr(runner, "tilstand", {"aktiv": {"issue": 1}, "resultater": {}})
    server = ThreadingHTTPServer(("127.0.0.1", 0), runner.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"

    def kald(sti, token=None, data=None):
        req = urllib.request.Request(url + sti, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"X-Fabrik-Token": token} if token else {})
        try:
            with urllib.request.urlopen(req) as s:
                return s.status, json.loads(s.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    try:
        assert kald("/helbred")[0] == 200
        assert kald("/status")[0] == 401
        assert kald("/status", "forkert")[0] == 401
        kode, data = kald("/status", "hemmelig")
        assert kode == 200 and data["ledig"] is False
        assert kald("/opgaver", "hemmelig", {"issue": 2, "opgave": "x"})[0] == 409  # optaget
        assert kald("/opgaver", "hemmelig", {"opgave": "x"})[0] == 400
    finally:
        server.shutdown()
