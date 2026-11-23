# Softwarefabrik

En lille softwarefabrik: jeg skriver en opgave som et GitHub-issue, et AI-trin i n8n forfiner den til en klar specifikation, og når jeg har godkendt den, bygger en kodeagent (Claude Code) den på sin egen branch og afleverer en pull request til mit review.

Fabrikken bygger en **Football Team Manager** (en terminal-app til et fodboldhold: spillere, kampe, mål og assists, statistik og træninger) i [`produkt/`](produkt/), og den bygger dele af sig selv.

> Issue #1 (en finance tracker) var fabrikkens første testkørsel. Derefter skiftede produktet til Football Team Manager.

```
Idé → Forfines → Klar til godkendelse → Godkendt → Bygges → Din QA → Færdig
                        ↑  (du kommenterer)    ↑ (kun dig)  ↓ ↓
                        └──────────────────────│──── Venter på dig (agenten spørger)
                                               └──── Sidder fast (fejl / over 30 min)
```

| Mappe/fil | Indhold |
|---|---|
| [`n8n/workflows/`](n8n/workflows/) | De 4 n8n-workflows som JSON (importeres i n8n) |
| [`n8n/prompts/forfining.md`](n8n/prompts/forfining.md) | Prompten til AI-trinnet, inkl. specifikationsskabelonen |
| [`runner/`](runner/) | Runneren: starter kodeagenten, håndhæver timeout og pusher branchen |
| [`scripts/`](scripts/) | Opret labels, generér workflows |
| [`docs/`](docs/) | [Arkitektur](docs/arkitektur.md), [specifikationsskabelon](docs/specifikationsskabelon.md), [evaluering](docs/evaluering.md) |
| [`opgaver/`](opgaver/) | Opgaveidéer til fabrikken |
| [`produkt/`](produkt/) | Det, fabrikken bygger |

## Opsætning

### 1. Forudsætninger
- Docker med n8n på `http://localhost:5678`
- Ollama med modellen fra `Konfiguration`-noden (standard `qwen3:4b`). Med Docker Desktop når n8n Ollama og runneren på værtens localhost via `host.docker.internal`, så begge kan nøjes med at lytte på 127.0.0.1.
- Python 3.12+ og git
- Claude Code CLI (`claude`) installeret og logget ind:
  ```powershell
  irm https://claude.ai/install.ps1 | iex
  ```

### 2. GitHub-repo og labels
Opret et **offentligt** repo `software-fabrik` på GitHub og push dette repo til det. Lav et fine-grained personal access token med adgang til repoet (Issues, Pull requests og Contents: read/write). Opret derefter labels:
```powershell
$env:GITHUB_TOKEN = "<dit token>"
```
```powershell
python scripts/opret_labels.py Thomas-dahl-01/software-fabrik
```
Anbefalet: beskyt `main` under *Settings → Branches*, så merge kræver en pull request.

### 3. Runner
```powershell
Copy-Item runner/.env.example runner/.env
```
Udfyld `FABRIK_REPO_URL` og en lang tilfældig `FABRIK_TOKEN` i `runner/.env`, og start runneren:
```powershell
python runner/runner.py
```

### 4. n8n
1. Opret to credentials i n8n:
   - **GitHub account** (type *GitHub API*): dit token (fx fra `gh auth token`). Ret id og navn i `GH_CRED` i `scripts/byg_workflows.py`, hvis din credential har et andet id
   - **Fabrik Runner** (type *Header Auth*): navn `X-Fabrik-Token`, værdi = `FABRIK_TOKEN` fra `runner/.env`
2. Importér de 4 filer fra `n8n/workflows/` (*Workflows → Import from file*), og vælg credentials i HTTP-noderne.
3. Tjek `Konfiguration`-noden i hvert workflow (ejer, repo, forfatter, model, URL'er).
4. Aktivér workflows. I basic A sættes `automatisk_runner` til `false` i workflow 2, og workflow 3 er inaktiv.

### Ændringer i workflows
Workflows genereres af [`scripts/byg_workflows.py`](scripts/byg_workflows.py). Ret dér (eller i prompten), og kør:
```powershell
python scripts/byg_workflows.py
```
Ændringen laves i en pull request, og efter review importeres JSON'en manuelt i n8n. Det manuelle trin er en del af kvalitetskontrollen.

## Sådan bruger du fabrikken
1. Opret et issue med en grov idé, og sæt labelen **Idé**.
2. Inden for et minut skriver AI-trinnet en forfinet specifikation og eventuelle spørgsmål som en kommentar (**Klar til godkendelse**). Kommentér for at rette, så forfines den igen.
3. Når du er tilfreds, sætter du selv labelen **Godkendt** (og fjerner Klar til godkendelse).
4. Fabrikken starter agenten (**Bygges**). Spørger den om noget, står spørgsmålet på issuet (**Venter på dig**): svar i en kommentar.
5. Når agenten er færdig, åbner fabrikken en PR (**Din QA**). Review, kør testene, og:
   - **merge**: opgaven bliver **Færdig**
   - **luk PR'en**: opgaven droppes og bliver **Færdig**
   - **send tilbage**: skriv en kommentar på *issuet* og sæt det til **Godkendt**. Agenten bygger videre på samme branch, og PR'en opdateres.
6. **Sidder fast**: sæt den til **Godkendt** for at prøve igen, eller luk issuet.

## Tests
```powershell
python -m pytest tests
```
Runneren testes med en falsk kodeagent mod et lokalt git-repo: færdig, spørgsmål, manglende status, timeout, at hemmeligheder ikke pushes, og token-kontrol.
