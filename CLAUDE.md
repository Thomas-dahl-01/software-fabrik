# Softwarefabrik: instruktioner til kodeagenten

Du arbejder i et repo, der indeholder en softwarefabrik og det produkt, fabrikken bygger. Skriv kode, kommentarer og commit-beskeder på dansk, men brug engelske/ASCII-navne til filer.

## Struktur
- `produkt/`: Football Team Manager, en terminal-app til et fodboldhold. Python 3.12+, kun standardbiblioteket (`sqlite3`, `argparse`) plus `pytest`. **Læs `produkt/README.md` før du ændrer noget**: den fastlægger strukturen (`produkt/fodbold/`-pakken, `db.py`, ét modul pr. område, `cli.py`) og konventionerne. Tests ligger i `produkt/tests/`.
- `runner/`: runneren (Python, kun standardbiblioteket). Tests i `tests/`.
- `n8n/workflows/*.json`: n8n-workflows. **Redigér dem ikke i hånden.** Ret i `scripts/byg_workflows.py` eller `n8n/prompts/` og kør `python scripts/byg_workflows.py`.
- `docs/`: arkitektur, skabelon og evaluering.

## Kommandoer
- Produkt-tests: `python -m pytest produkt`
- Fabrik-tests: `python -m pytest tests`
- Generér workflows: `python scripts/byg_workflows.py`

## Regler
- Opgaver om produktet må kun ændre filer i `produkt/`.
- Tilføj ikke nye afhængigheder uden at specifikationen beder om det.
- Rør aldrig `.env`-filer eller hemmeligheder.
- Alle nye funktioner skal have tests, og alle tests skal bestå.
