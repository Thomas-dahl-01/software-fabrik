"""Opretter (eller opdaterer) fabrikkens tilstands-labels på GitHub-repoet.

Brug:
    $env:GITHUB_TOKEN = "<token med repo-adgang>"
    python scripts/opret_labels.py <ejer>/<repo>
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Navn, farve, beskrivelse. Orange = du handler, lilla = AI arbejder, pink = n8n flytter videre.
LABELS = [
    ("Idé", "F28C28", "Du har skrevet en grov opgave"),
    ("Forfines", "8E44AD", "AI-trinnet i n8n omskriver opgaven efter skabelonen"),
    ("Klar til godkendelse", "F28C28", "Læs AI'ens version: kommentér eller flyt til Godkendt"),
    ("Godkendt", "E91E63", "Venter på fabrikken (kun du sætter denne)"),
    ("Bygges", "8E44AD", "Kodeagenten arbejder på branch issue-N"),
    ("Venter på dig", "F28C28", "Agenten har et spørgsmål: svar i en kommentar"),
    ("Sidder fast", "F28C28", "Agenten fejlede eller kørte over 30 min: flyt til Godkendt eller luk"),
    ("Din QA", "F28C28", "Pull request klar til dit review"),
    ("Færdig", "2E7D32", "Pull request merget eller issue lukket"),
]


def kald(metode: str, url: str, token: str, data: dict | None = None) -> int:
    req = urllib.request.Request(
        url,
        method=metode,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as svar:
            return svar.status
    except urllib.error.HTTPError as fejl:
        return fejl.code


def main() -> None:
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        sys.exit("Brug: python scripts/opret_labels.py <ejer>/<repo>")
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("Sæt GITHUB_TOKEN først")
    base = f"https://api.github.com/repos/{sys.argv[1]}/labels"
    for navn, farve, beskrivelse in LABELS:
        data = {"name": navn, "color": farve, "description": beskrivelse}
        status = kald("POST", base, token, data)
        if status == 422:  # findes allerede -> opdater
            status = kald("PATCH", f"{base}/{urllib.parse.quote(navn)}", token, data)
        print(f"{status}  {navn}")


if __name__ == "__main__":
    main()
