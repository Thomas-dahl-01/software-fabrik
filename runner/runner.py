"""Softwarefabrikkens runner.

Et lille HTTP-program, som n8n kalder. Det gør kun det, n8n ikke kan:
checker repoet ud på branchen issue-N, starter kodeagenten med opgaven som prompt,
pusher branchen og gemmer resultatet: faerdig, spoergsmaal eller sidder_fast.

Runneren svarer n8n med det samme og arbejder i baggrunden. n8n spørger efter
resultater på et skema (GET /status) og kvitterer, når de er håndteret.

Kun standardbiblioteket bruges. Start med:  python runner/runner.py
"""

from __future__ import annotations

import hmac
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAPPE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- konfiguration

def laes_env(fil: Path) -> None:
    """Indlæs KEY=VALUE-linjer fra runner/.env, uden at overskrive miljøet."""
    if not fil.exists():
        return
    for linje in fil.read_text(encoding="utf-8").splitlines():
        linje = linje.strip()
        if linje and not linje.startswith("#") and "=" in linje:
            noegle, vaerdi = linje.split("=", 1)
            os.environ.setdefault(noegle.strip(), vaerdi.strip().strip('"'))


laes_env(MAPPE / ".env")

REPO_URL = os.environ.get("FABRIK_REPO_URL", "")
TOKEN = os.environ.get("FABRIK_TOKEN", "")
VAERT = os.environ.get("FABRIK_VAERT", "0.0.0.0")
PORT = int(os.environ.get("FABRIK_PORT", "8765"))
AGENT = os.environ.get("FABRIK_AGENT", "claude")
MODEL = os.environ.get("FABRIK_MODEL", "")  # tom = agentens standardmodel
TIMEOUT_SEK = int(float(os.environ.get("FABRIK_TIMEOUT_MIN", "30")) * 60)
MAX_TURNS = os.environ.get("FABRIK_MAX_TURNS", "80")
ARBEJDE = Path(os.environ.get("FABRIK_ARBEJDSMAPPE", MAPPE / "arbejde"))
REPO = ARBEJDE / "repo"
LOGS = MAPPE / "logs"
TILSTAND_FIL = MAPPE / "tilstand.json"

# Hvad agenten må uden at spørge. Alt andet afvises i headless-tilstand.
TILLADTE_VAERKTOEJER = [
    "Read", "Edit", "Write", "Glob", "Grep", "TodoWrite",
    "Bash(python:*)", "Bash(python3:*)", "Bash(py:*)", "Bash(pytest:*)",
    "Bash(pip install:*)",
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
    "Bash(git add:*)", "Bash(git commit:*)",
    "Bash(ls:*)", "Bash(cat:*)", "Bash(mkdir:*)",
]
FORBUDTE_VAERKTOEJER = [
    "WebFetch", "WebSearch",
    "Bash(git push:*)", "Bash(git checkout:*)", "Bash(git switch:*)",
    "Bash(git reset:*)", "Bash(git rebase:*)", "Bash(git remote:*)",
    "Bash(curl:*)", "Bash(wget:*)", "Bash(rm -rf:*)",
]
# Filer der aldrig må pushes, uanset hvad agenten har lavet.
FORBUDTE_FILER = re.compile(r"(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*|credentials.*\.json)$")


# ---------------------------------------------------------------- tilstand

laas = threading.Lock()
tilstand: dict = {"aktiv": None, "resultater": {}}


def gem_tilstand() -> None:
    TILSTAND_FIL.write_text(json.dumps(tilstand, ensure_ascii=False, indent=2), encoding="utf-8")


def indlaes_tilstand() -> None:
    global tilstand
    if TILSTAND_FIL.exists():
        tilstand = json.loads(TILSTAND_FIL.read_text(encoding="utf-8"))
    if tilstand.get("aktiv"):
        # Runneren blev stoppet midt i en kørsel: meld den som sidder fast.
        issue = tilstand["aktiv"]["issue"]
        tilstand["resultater"][str(issue)] = resultat(
            issue, "sidder_fast", opsummering="Runneren blev genstartet midt i kørslen.")
        tilstand["aktiv"] = None
        gem_tilstand()


def nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resultat(issue: int, status: str, **felter) -> dict:
    return {
        "issue": issue,
        "branch": f"issue-{issue}",
        "status": status,
        "opsummering": felter.get("opsummering", ""),
        "tests": felter.get("tests", ""),
        "spoergsmaal": felter.get("spoergsmaal", ""),
        "commits": felter.get("commits", 0),
        "filer": felter.get("filer", []),
        "varighed_sek": felter.get("varighed_sek", 0),
        "pris_usd": felter.get("pris_usd"),
        "antal_ture": felter.get("antal_ture"),
        "log_hale": felter.get("log_hale", ""),
        "afsluttet": nu(),
    }


# ---------------------------------------------------------------- git

def git(*args: str, tjek: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if tjek and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} fejlede:\n{p.stderr.strip()}")
    return p.stdout.strip()


def forbered_branch(branch: str) -> None:
    ARBEJDE.mkdir(parents=True, exist_ok=True)
    if not (REPO / ".git").exists():
        if not REPO_URL:
            raise RuntimeError("FABRIK_REPO_URL er ikke sat i runner/.env")
        subprocess.run(["git", "clone", REPO_URL, str(REPO)], check=True)
    git("fetch", "origin", "--prune")
    git("reset", "--hard")
    git("clean", "-fdx", "-e", ".venv")
    findes = git("ls-remote", "--heads", "origin", branch)
    start = f"origin/{branch}" if findes else "origin/main"
    git("checkout", "-B", branch, start)


def commit_rest(branch: str, titel: str) -> None:
    git("add", "-A")
    if git("diff", "--cached", "--name-only"):
        git("commit", "-m", f"{branch}: {titel}\n\nLavet af kodeagenten via softwarefabrikken.")


def aendrede_filer() -> list[str]:
    ud = git("diff", "--name-only", "origin/main...HEAD", tjek=False)
    return [f for f in ud.splitlines() if f]


def push(branch: str) -> None:
    farlige = [f for f in aendrede_filer() if FORBUDTE_FILER.search(f)]
    if farlige:
        raise RuntimeError(f"Push afvist: branchen indeholder følsomme filer: {farlige}")
    git("push", "--force-with-lease", "origin", f"{branch}:{branch}")


# ---------------------------------------------------------------- agent

STATUS_BLOK = re.compile(r"```fabrik-status\s*(\{.*?\})\s*```", re.DOTALL)
NORMALISER = {
    "faerdig": "faerdig", "færdig": "faerdig", "done": "faerdig",
    "spoergsmaal": "spoergsmaal", "spørgsmål": "spoergsmaal", "question": "spoergsmaal",
    "sidder_fast": "sidder_fast", "stuck": "sidder_fast",
}


def agent_kommando() -> list[str]:
    exe = shutil.which(AGENT) or AGENT
    kmd = [exe, "-p", "--output-format", "json", "--permission-mode", "acceptEdits",
           "--max-turns", str(MAX_TURNS),
           "--allowedTools", *TILLADTE_VAERKTOEJER,
           "--disallowedTools", *FORBUDTE_VAERKTOEJER]
    if MODEL:
        kmd += ["--model", MODEL]
    return kmd


def stop_proces(p: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        os.killpg(p.pid, signal.SIGKILL)


def koer_agent(prompt: str, logfil: Path) -> tuple[str, dict, bool]:
    """Kør agenten. Returnerer (rå output, parsed json, timeout?)."""
    ekstra = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" \
        else {"start_new_session": True}
    p = subprocess.Popen(agent_kommando(), cwd=REPO, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", **ekstra)
    try:
        ud, _ = p.communicate(prompt, timeout=TIMEOUT_SEK)
        timeout = False
    except subprocess.TimeoutExpired:
        stop_proces(p)
        ud, _ = p.communicate()
        timeout = True
    logfil.write_text(ud or "", encoding="utf-8")
    try:
        data = json.loads(ud.strip().splitlines()[-1]) if ud and ud.strip() else {}
    except (json.JSONDecodeError, IndexError):
        data = {}
    return ud or "", data, timeout


def fortolk_status(tekst: str) -> dict | None:
    fund = STATUS_BLOK.findall(tekst or "")
    if not fund:
        return None
    try:
        blok = json.loads(fund[-1])
    except json.JSONDecodeError:
        return None
    blok["status"] = NORMALISER.get(str(blok.get("status", "")).strip().lower())
    return blok if blok["status"] else None


# ---------------------------------------------------------------- en kørsel

def koer_opgave(issue: int, titel: str, opgave: str) -> None:
    branch = f"issue-{issue}"
    start = time.monotonic()
    LOGS.mkdir(exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    logfil = LOGS / f"{branch}-{stempel}.log"
    try:
        forbered_branch(branch)
        instruks = (MAPPE / "agent_instruks.md").read_text(encoding="utf-8")
        prompt = (instruks.replace("{{BRANCH}}", branch)
                  .replace("{{ISSUE}}", str(issue))
                  .replace("{{OPGAVE}}", opgave))
        raa, data, timeout = koer_agent(prompt, logfil)
        varighed = int(time.monotonic() - start)
        tekst = data.get("result", "") if isinstance(data, dict) else ""
        felles = dict(varighed_sek=varighed, pris_usd=data.get("total_cost_usd"),
                      antal_ture=data.get("num_turns"), log_hale=raa[-1500:])

        if timeout:
            res = resultat(issue, "sidder_fast",
                           opsummering=f"Agenten blev stoppet efter {TIMEOUT_SEK // 60} minutter.", **felles)
        else:
            blok = fortolk_status(tekst)
            if blok is None:
                res = resultat(issue, "sidder_fast",
                               opsummering="Agenten afsluttede uden en gyldig statusblok.", **felles)
            else:
                res = resultat(issue, blok["status"], opsummering=blok.get("opsummering", ""),
                               tests=blok.get("tests", ""), spoergsmaal=blok.get("spoergsmaal", ""),
                               **felles)

        # Gem agentens arbejde på branchen, også ved spørgsmål, så intet går tabt.
        commit_rest(branch, titel)
        antal = int(git("rev-list", "--count", "origin/main..HEAD", tjek=False) or 0)
        res["commits"] = antal
        res["filer"] = aendrede_filer()
        if res["status"] == "faerdig" and antal == 0:
            res["status"] = "sidder_fast"
            res["opsummering"] = "Agenten meldte færdig, men lavede ingen ændringer.\n" + res["opsummering"]
        if antal > 0:
            push(branch)
    except Exception as fejl:  # alt uventet ender som "sidder fast" med forklaring
        res = resultat(issue, "sidder_fast", opsummering=f"Runner-fejl: {fejl}",
                       varighed_sek=int(time.monotonic() - start))

    with (LOGS / "koersler.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({k: v for k, v in res.items() if k != "log_hale"}, ensure_ascii=False) + "\n")
    with laas:
        tilstand["resultater"][str(issue)] = res
        tilstand["aktiv"] = None
        gem_tilstand()
    print(f"[{nu()}] issue-{issue}: {res['status']} ({res['varighed_sek']} s)", flush=True)


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    def svar(self, kode: int, data: dict) -> None:
        krop = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(kode)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(krop)))
        self.end_headers()
        self.wfile.write(krop)

    def godkendt(self) -> bool:
        if TOKEN and hmac.compare_digest(self.headers.get("X-Fabrik-Token", ""), TOKEN):
            return True
        self.svar(401, {"fejl": "forkert eller manglende X-Fabrik-Token"})
        return False

    def do_GET(self) -> None:
        if self.path == "/helbred":
            return self.svar(200, {"ok": True})
        if not self.godkendt():
            return
        if self.path == "/status":
            with laas:
                aktiv = tilstand["aktiv"]
                return self.svar(200, {
                    "aktiv": aktiv,
                    "ledig": aktiv is None,
                    "resultater": list(tilstand["resultater"].values()),
                })
        self.svar(404, {"fejl": "ukendt sti"})

    def do_POST(self) -> None:
        if not self.godkendt():
            return
        laengde = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(laengde) or b"{}")
        except json.JSONDecodeError:
            return self.svar(400, {"fejl": "ugyldig JSON"})

        if self.path == "/opgaver":
            try:
                issue = int(data["issue"])
                titel = str(data.get("titel", ""))[:100]
                opgave = str(data["opgave"])
            except (KeyError, ValueError, TypeError):
                return self.svar(400, {"fejl": "kræver issue (tal) og opgave (tekst)"})
            with laas:
                if tilstand["aktiv"]:
                    return self.svar(409, {"fejl": "runneren er optaget", "aktiv": tilstand["aktiv"]})
                tilstand["aktiv"] = {"issue": issue, "titel": titel, "startet": nu()}
                tilstand["resultater"].pop(str(issue), None)
                gem_tilstand()
            threading.Thread(target=koer_opgave, args=(issue, titel, opgave), daemon=True).start()
            return self.svar(202, {"modtaget": True, "issue": issue, "branch": f"issue-{issue}"})

        m = re.fullmatch(r"/resultater/(\d+)/kvitter", self.path)
        if m:
            with laas:
                fjernet = tilstand["resultater"].pop(m.group(1), None)
                gem_tilstand()
            return self.svar(200, {"kvitteret": fjernet is not None})
        self.svar(404, {"fejl": "ukendt sti"})

    def log_message(self, fmt: str, *args) -> None:
        if "/helbred" not in (args[0] if args else ""):
            sys.stderr.write(f"[{nu()}] {fmt % args}\n")


def main() -> None:
    if not TOKEN:
        sys.exit("Sæt FABRIK_TOKEN i runner/.env (en lang tilfældig streng, samme som i n8n)")
    indlaes_tilstand()
    print(f"Runner lytter på http://{VAERT}:{PORT}  agent={AGENT}  timeout={TIMEOUT_SEK // 60} min")
    ThreadingHTTPServer((VAERT, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
