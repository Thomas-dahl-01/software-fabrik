"""Genererer fabrikkens n8n-workflows som JSON i n8n/workflows/.

Kilden til sandheden er dette script og n8n/prompts/forfining.md. Kør:
    python scripts/byg_workflows.py
og importér derefter JSON-filerne i n8n efter review (Workflows -> Import from file).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROD = Path(__file__).resolve().parent.parent
UD = ROD / "n8n" / "workflows"
PROMPT = (ROD / "n8n" / "prompts" / "forfining.md").read_text(encoding="utf-8")

K = "$('Konfiguration').first().json"
GH = "https://api.github.com/repos/{{ " + K + ".ejer }}/{{ " + K + ".repo }}"
GH_CRED = {"githubApi": {"id": "7l2RzCfRxIwesUNF", "name": "GitHub account"}}
RUNNER_CRED = {"httpHeaderAuth": {"id": "fabrik-runner", "name": "Fabrik Runner"}}

# Fælles JavaScript-hjælpere, som indsættes øverst i alle Code-noder.
FAELLES_JS = r"""
const TILSTANDE = ['Idé', 'Forfines', 'Klar til godkendelse', 'Godkendt', 'Bygges',
                   'Venter på dig', 'Sidder fast', 'Din QA', 'Færdig'];
const K = $('Konfiguration').first().json;
const navne = (issue) => (issue.labels || []).map(l => typeof l === 'string' ? l : l.name);
const tilstandAf = (issue) => navne(issue).find(n => TILSTANDE.includes(n)) || null;
const labelsMed = (issue, ny) => (issue ? navne(issue) : []).filter(n => !TILSTANDE.includes(n)).concat([ny]);
const erFabrik = (k) => (k.body || '').includes('<!-- fabrik');
const issueNr = (url) => Number(String(url).split('/').pop());
const renser = (t) => (t || '').replace(/<!--[\s\S]*?-->/g, '').trim();
const mine = (liste) => liste.map(i => i.json).filter(i => i.number && !i.pull_request &&
  (i.user?.login || '').toLowerCase() === String(K.forfatter).toLowerCase());
""".strip()


# ------------------------------------------------------------------ node-byggere

def node(navn, type_, version, x, y, parametre, **ekstra):
    n = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, navn + type_ + str(x) + str(y))),
         "name": navn, "type": type_, "typeVersion": version,
         "position": [x, y], "parameters": parametre}
    n.update(ekstra)
    return n


def tidsplan(x=0, y=0, minutter=1):
    return node("Hvert minut", "n8n-nodes-base.scheduleTrigger", 1.2, x, y,
                {"rule": {"interval": [{"field": "minutes", "minutesInterval": minutter}]}})


def manuel(x=0, y=200):
    return node("Kør manuelt", "n8n-nodes-base.manualTrigger", 1, x, y, {})


def konfiguration(x, y, felter: dict):
    tildelinger = []
    for navn, vaerdi in felter.items():
        tildelinger.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, navn)), "name": navn,
                            "value": vaerdi, "type": "boolean" if isinstance(vaerdi, bool) else "string"})
    return node("Konfiguration", "n8n-nodes-base.set", 3.4, x, y,
                {"assignments": {"assignments": tildelinger}, "options": {}})


def kode(navn, x, y, js, medFaelles=True):
    return node(navn, "n8n-nodes-base.code", 2, x, y,
                {"jsCode": (FAELLES_JS + "\n\n" if medFaelles else "") + js.strip()})


def http(navn, x, y, metode, url, krop=None, query=None, cred="github", timeout=30000, **ekstra):
    p = {"method": metode, "url": "=" + url}
    if cred == "github":
        p.update({"authentication": "predefinedCredentialType", "nodeCredentialType": "githubApi"})
    elif cred == "runner":
        p.update({"authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"})
    if query:
        p.update({"sendQuery": True, "queryParameters": {"parameters": [
            {"name": k, "value": v} for k, v in query.items()]}})
    if krop is not None:
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify(" + krop + ") }}"})
    p["options"] = {"timeout": timeout}
    creds = GH_CRED if cred == "github" else RUNNER_CRED if cred == "runner" else None
    if creds:
        ekstra["credentials"] = creds
    return node(navn, "n8n-nodes-base.httpRequest", 4.2, x, y, p, **ekstra)


def hvis(navn, x, y, udtryk):
    return node(navn, "n8n-nodes-base.if", 2, x, y, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, navn)), "leftValue": "={{ " + udtryk + " }}",
                            "rightValue": "", "operator": {"type": "boolean", "operation": "true",
                                                           "singleValue": True}}],
            "combinator": "and"},
        "options": {}})


def note(tekst, x, y, bredde=520, hoejde=260):
    return node("Beskrivelse", "n8n-nodes-base.stickyNote", 1, x, y,
                {"content": tekst, "width": bredde, "height": hoejde})


def workflow(navn, noder, kanter):
    forbindelser: dict = {}
    for kant in kanter:
        fra, til, *udgang = kant
        idx = udgang[0] if udgang else 0
        main = forbindelser.setdefault(fra, {"main": []})["main"]
        while len(main) <= idx:
            main.append([])
        main[idx].append({"node": til, "type": "main", "index": 0})
    # Fast id ("fabrikWorkflow01" osv.), så en genimport via n8n's CLI overskriver i stedet for at lave dubletter.
    wf_id = "fabrikWorkflow0" + navn.split("·")[0].strip().split()[-1]
    return {"id": wf_id, "name": navn, "nodes": noder, "connections": forbindelser,
            "settings": {"executionOrder": "v1"}, "active": False, "pinData": {}}


def kaede(*navne):
    return [(a, b) for a, b in zip(navne, navne[1:])]


FELLES_KONFIG = {
    "ejer": "Thomas-dahl-01",
    "repo": "software-fabrik",
    "forfatter": "Thomas-dahl-01",
}

ISSUES_QUERY = {"state": "open", "per_page": "100", "sort": "created", "direction": "asc"}
ALTID = {"alwaysOutputData": True}


# ------------------------------------------------------------------ 1: forfin opgave

def wf_forfin():
    vaelg = r"""
const issues = mine($('Hent åbne issues').all());
const seneste = {};
for (const k of $('Hent seneste kommentarer').all().map(i => i.json).filter(k => k.id)) {
  const n = issueNr(k.issue_url);
  if (!seneste[n] || k.created_at > seneste[n].created_at) seneste[n] = k;
}
const tiMinSiden = new Date(Date.now() - 10 * 60 * 1000).toISOString();
const kandidater = issues.filter(i => {
  const t = tilstandAf(i), s = seneste[i.number];
  if (t === 'Idé') return true;                                   // ny grov opgave
  if (t === 'Klar til godkendelse') return s && !erFabrik(s);     // du har kommenteret -> forfin igen
  if (t === 'Forfines') return i.updated_at < tiMinSiden;         // hang fra en afbrudt kørsel
  return false;
});
// Én opgave pr. kørsel, så AI-kald ikke overlapper.
return kandidater.slice(0, 1).map(i => ({ json: {
  number: i.number,
  labels_forfines: labelsMed(i, 'Forfines'),
  labels_klar: labelsMed(i, 'Klar til godkendelse'),
}}));
"""
    besvarede = r"""
const issues = mine($('Hent åbne issues').all());
const seneste = {};
for (const k of $('Hent seneste kommentarer').all().map(i => i.json).filter(k => k.id)) {
  const n = issueNr(k.issue_url);
  if (!seneste[n] || k.created_at > seneste[n].created_at) seneste[n] = k;
}
// Agenten spurgte, og den nyeste kommentar er din -> tilbage til Godkendt.
return issues
  .filter(i => tilstandAf(i) === 'Venter på dig' && seneste[i.number] && !erFabrik(seneste[i.number]))
  .map(i => ({ json: { number: i.number, labels: labelsMed(i, 'Godkendt') } }));
"""
    byg_prompt = r"""
const PROMPT = """ + json.dumps(PROMPT, ensure_ascii=False) + r""";
const valgt = $('Vælg opgave til forfining').first().json;
const issue = $('Hent åbne issues').all().map(i => i.json).find(i => i.number === valgt.number);
const kommentarer = $('Hent issue-kommentarer').all().map(i => i.json).filter(k => k.id);
const samtale = kommentarer.map(k =>
  `### ${erFabrik(k) ? 'Fabrikken (din tidligere version eller agentens spørgsmål)' : 'Udvikleren'} – ${k.created_at}\n${renser(k.body)}`
).join('\n\n');
const system = PROMPT.replace('{{REPO_KONTEKST}}', K.repo_kontekst);
const bruger = [
  `# Issue #${issue.number}: ${issue.title}`, '',
  '## Udviklerens grove beskrivelse', issue.body || '(ingen beskrivelse)', '',
  '## Samtale indtil nu', samtale || '(ingen kommentarer endnu)', '',
  'Skriv nu den forfinede opgave som ét JSON-objekt.',
].join('\n');
return [{ json: { number: issue.number, messages: [
  { role: 'system', content: system },
  { role: 'user', content: bruger },
]}}];
"""
    formater = r"""
const valgt = $('Vælg opgave til forfining').first().json;
const raa = $json.message?.content ?? '';
// Den lille lokale model (qwen3:4b) skriver af og til kinesiske tegn i stedet for æøå,
// fx "m氓" for "må", "v忙re" for "være" og "f酶rste" for "første" (set i issue #5).
// De kendte erstattes, og findes der stadig CJK-tegn, får du en advarsel i kommentaren.
const RETTELSER = { '氓': 'å', '忙': 'æ', '酶': 'ø' };
const ret = (v) => typeof v === 'string' ? v.replace(/[氓忙酶]/g, c => RETTELSER[c])
  : Array.isArray(v) ? v.map(ret)
  : (v && typeof v === 'object') ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, ret(x)])) : v;
let s = null;
try { s = ret(JSON.parse(raa.replace(/^\s*```(json)?/, '').replace(/```\s*$/, '').trim())); } catch (e) {}
const cjk = s ? (JSON.stringify(s).match(/[㐀-鿿]/g) || []) : [];
const liste = (a) => (Array.isArray(a) && a.length) ? a.map(x => `- ${x}`).join('\n') : '- (ingen)';
const tjek = (a) => (Array.isArray(a) && a.length) ? a.map(x => `- [ ] ${x}`).join('\n') : '- (ingen)';
let krop;
if (!s) {
  krop = `<!-- fabrik:spec-fejl -->\n⚠️ AI-trinnet returnerede ikke gyldig JSON. Skriv en kommentar for at prøve igen.\n\n<details><summary>Rå svar</summary>\n\n${raa}\n</details>`;
} else {
  const v = s.vurdering || {};
  krop = [
    '<!-- fabrik:spec -->',
    `## 🤖 Forfinet opgave: ${s.titel}`, '',
    '### Mål', s.maal, '',
    '### Hvorfor', s.hvorfor, '',
    '### Omfang', liste(s.omfang), '',
    '### Uden for omfang', liste(s.uden_for_omfang), '',
    '### Begrænsninger', liste(s.begraensninger), '',
    '### Acceptkriterier', tjek(s.acceptkriterier), '',
    '### Tests', liste(s.tests), '',
    '### Område i repoet', liste(s.omraade), '',
    '### Antagelser', liste(s.antagelser), '',
    '---',
    '### ❓ Spørgsmål til dig', liste(s.spoergsmaal), '',
    '### 💡 AI\'ens vurdering', `**Størrelse:** ${v.stoerrelse ?? '?'} · **Risiko:** ${v.risiko ?? '?'}`, '',
    v.anbefaling ?? '', '',
    cjk.length ? `> ⚠️ Modellen skrev tegn, der ikke er dansk (${[...new Set(cjk)].join(' ')}). Læs teksten ekstra grundigt.\n` : '',
    '---',
    '_Svar eller ret i en kommentar, så forfiner jeg igen. Når du er tilfreds, flytter du selv opgaven til **Godkendt**._',
  ].join('\n');
}
return [{ json: { number: valgt.number, body: krop, labels: valgt.labels_klar } }];
"""
    konfig = dict(FELLES_KONFIG,
                  ollama_url="http://host.docker.internal:11434",
                  model="qwen3:4b",
                  repo_kontekst=(
                      "Ét repo med to dele: (1) fabrikken selv: n8n-workflows som JSON i n8n/workflows/ "
                      "(genereres af scripts/byg_workflows.py) og runneren i runner/ (Python, kun standardbiblioteket). "
                      "(2) Produktet i produkt/: Football Team Manager, et administrationssystem til et fodboldhold "
                      "som terminal-app. Python 3.12+, kun standardbiblioteket (sqlite3, argparse) og pytest. "
                      "Fast struktur: pakken produkt/fodbold/ med db.py (SQLite-forbindelse, db.forbind()), ét modul "
                      "pr. område (fx spillere.py, kampe.py) med funktioner der tager en sqlite3.Connection, og "
                      "cli.py (argparse, køres med 'python -m fodbold' fra produkt/). Tests i produkt/tests/ med "
                      "':memory:'-database. Funktions- og tabelnavne på dansk uden æøå. Opgaver om produktet må kun "
                      "ændre filer i produkt/. Byg videre på eksisterende moduler i stedet for at lave nye løsninger. "
                      "Kør tests med: python -m pytest produkt"))
    V = "$('Vælg opgave til forfining').first().json"
    F = "$('Formater kommentar').first().json"
    noder = [
        note("## 1 · Forfin opgave\n**Idé → Forfines → Klar til godkendelse**\n\n"
             "Øverst: AI-trinnet omskriver den grove opgave efter skabelonen og stiller spørgsmål.\n"
             "Kommenterer du på en opgave i *Klar til godkendelse*, forfines den igen.\n\n"
             "Nederst: svarer du på agentens spørgsmål (*Venter på dig*), flyttes opgaven til *Godkendt*.\n\n"
             "AI'en rådgiver, den godkender aldrig.", -40, -320, 560, 260),
        tidsplan(0, 0), manuel(0, 200),
        konfiguration(220, 100, konfig),
        http("Hent åbne issues", 440, 100, "GET", GH + "/issues", query=ISSUES_QUERY, executeOnce=True, **ALTID),
        http("Hent seneste kommentarer", 660, 100, "GET", GH + "/issues/comments",
             query={"sort": "created", "direction": "desc", "per_page": "100"}, executeOnce=True, **ALTID),
        kode("Vælg opgave til forfining", 880, 0, vaelg),
        http("Sæt Forfines", 1100, 0, "PATCH", GH + "/issues/{{ " + V + ".number }}",
             krop="{ labels: " + V + ".labels_forfines }"),
        http("Hent issue-kommentarer", 1320, 0, "GET", GH + "/issues/{{ " + V + ".number }}/comments",
             query={"per_page": "100"}, **ALTID),
        kode("Byg prompt", 1540, 0, byg_prompt),
        http("AI-trin (Ollama)", 1760, 0, "POST", "{{ " + K + ".ollama_url }}/api/chat",
             krop="{ model: " + K + ".model, messages: $json.messages, stream: false, format: 'json', think: false, "
                  "options: { temperature: 0.2 } }", cred=None, timeout=600000),
        kode("Formater kommentar", 1980, 0, formater),
        http("Skriv forfinet opgave", 2200, 0, "POST", GH + "/issues/{{ " + F + ".number }}/comments",
             krop="{ body: " + F + ".body }"),
        http("Sæt Klar til godkendelse", 2420, 0, "PATCH", GH + "/issues/{{ " + F + ".number }}",
             krop="{ labels: " + F + ".labels }"),
        kode("Find besvarede spørgsmål", 880, 260, besvarede),
        http("Sæt Godkendt", 1100, 260, "PATCH", GH + "/issues/{{ $json.number }}", krop="{ labels: $json.labels }"),
        http("Kvittér for svar", 1320, 260, "POST", GH + "/issues/{{ $json.number }}/comments",
             krop="{ body: '<!-- fabrik:svar-modtaget -->\\n↩️ Svar modtaget. Opgaven er flyttet tilbage til "
                  "**Godkendt** og bygges igen med dit svar, når fabrikken har plads.' }"),
    ]
    kanter = [("Hvert minut", "Konfiguration"), ("Kør manuelt", "Konfiguration"),
              *kaede("Konfiguration", "Hent åbne issues", "Hent seneste kommentarer"),
              *kaede("Hent seneste kommentarer", "Vælg opgave til forfining", "Sæt Forfines",
                     "Hent issue-kommentarer", "Byg prompt", "AI-trin (Ollama)", "Formater kommentar",
                     "Skriv forfinet opgave", "Sæt Klar til godkendelse"),
              *kaede("Hent seneste kommentarer", "Find besvarede spørgsmål", "Sæt Godkendt", "Kvittér for svar")]
    return workflow("Fabrik 1 · Forfin opgave", noder, kanter)


# ------------------------------------------------------------------ 2: start opgave

def wf_start():
    vaelg = r"""
const issues = mine($('Hent åbne issues').all());
if (issues.some(i => tilstandAf(i) === 'Bygges')) return [];   // én opgave ad gangen
const naeste = issues.filter(i => tilstandAf(i) === 'Godkendt').sort((a, b) => a.number - b.number)[0];
if (!naeste) return [];
return [{ json: {
  number: naeste.number, titel: naeste.title, body: naeste.body || '',
  labels: labelsMed(naeste, 'Bygges'), automatisk: K.automatisk_runner === true || K.automatisk_runner === 'true',
}}];
"""
    ledig = r"""
if ($json.ledig !== true) return [];   // runneren er optaget eller nede -> prøv igen næste minut
return [$('Vælg næste opgave').first()];
"""
    byg = r"""
const v = $('Vælg næste opgave').first().json;
const k = $('Hent issue-kommentarer').all().map(i => i.json).filter(x => x.id);
let specIdx = -1;
k.forEach((x, i) => { if ((x.body || '').includes('<!-- fabrik:spec -->')) specIdx = i; });
const spec = specIdx >= 0
  ? renser(k[specIdx].body).split('\n').filter(l => !l.startsWith('_Svar eller ret')).join('\n').trim()
  : null;
const efter = k.slice(specIdx + 1).map(x =>
  `**${erFabrik(x) ? 'Fabrikken' : 'Udvikleren'}** (${x.created_at}):\n${renser(x.body)}`).join('\n\n');
const opgave = [
  `# Issue #${v.number}: ${v.titel}`, '',
  '## Gældende specifikation', spec || v.body || '(ingen)', '',
  '## Udviklerens oprindelige beskrivelse', v.body || '(ingen)', '',
  '## Kommentarer efter specifikationen (svar og feedback fra udvikleren har forrang)', efter || '(ingen)',
].join('\n');
return [{ json: { issue: v.number, titel: v.titel, opgave } }];
"""
    V = "$('Vælg næste opgave').first().json"
    B = "$('Byg opgave til agenten').first().json"
    konfig = dict(FELLES_KONFIG, runner_url="http://host.docker.internal:8765", automatisk_runner=True)
    noder = [
        note("## 2 · Start opgave\n**Godkendt → Bygges**\n\n"
             "Kun opgaver du selv har skrevet, og kun én ad gangen.\n\n"
             "*automatisk_runner = true* (basic B): runneren starter kodeagenten på branch issue-N.\n"
             "*automatisk_runner = false* (basic A): opgaven markeres Bygges, og du starter agenten selv.",
             -40, -320, 560, 240),
        tidsplan(0, 0), manuel(0, 200),
        konfiguration(220, 100, konfig),
        http("Hent åbne issues", 440, 100, "GET", GH + "/issues", query=ISSUES_QUERY, **ALTID),
        kode("Vælg næste opgave", 660, 100, vaelg),
        hvis("Automatisk runner?", 880, 100, "$json.automatisk"),
        http("Spørg runner", 1100, 0, "GET", "{{ " + K + ".runner_url }}/status", cred="runner",
             onError="continueRegularOutput"),
        kode("Er runneren ledig?", 1320, 0, ledig, medFaelles=False),
        http("Hent issue-kommentarer", 1540, 0, "GET", GH + "/issues/{{ " + V + ".number }}/comments",
             query={"per_page": "100"}, **ALTID),
        kode("Byg opgave til agenten", 1760, 0, byg),
        http("Sæt Bygges", 1980, 0, "PATCH", GH + "/issues/{{ " + V + ".number }}", krop="{ labels: " + V + ".labels }"),
        http("Send til runner", 2200, 0, "POST", "{{ " + K + ".runner_url }}/opgaver",
             krop="{ issue: " + B + ".issue, titel: " + B + ".titel, opgave: " + B + ".opgave }", cred="runner"),
        http("Kommentér: agent startet", 2420, 0, "POST", GH + "/issues/{{ " + V + ".number }}/comments",
             krop="{ body: '<!-- fabrik:startet -->\\n🏗️ Kodeagenten er gået i gang på branch `issue-' + "
                  + V + ".number + '`. Den stopper senest efter 30 minutter.' }"),
        http("Sæt Bygges (manuel)", 1100, 220, "PATCH", GH + "/issues/{{ " + V + ".number }}",
             krop="{ labels: " + V + ".labels }"),
        http("Kommentér: start agenten selv", 1320, 220, "POST", GH + "/issues/{{ " + V + ".number }}/comments",
             krop="{ body: '<!-- fabrik:manuel -->\\n🏗️ Opgaven er markeret **Bygges**. Start kodeagenten selv på "
                  "branch `issue-' + " + V + ".number + '` med issuet som input, og åbn en pull request fra den branch.' }"),
    ]
    kanter = [("Hvert minut", "Konfiguration"), ("Kør manuelt", "Konfiguration"),
              *kaede("Konfiguration", "Hent åbne issues", "Vælg næste opgave", "Automatisk runner?"),
              ("Automatisk runner?", "Spørg runner", 0),
              *kaede("Spørg runner", "Er runneren ledig?", "Hent issue-kommentarer", "Byg opgave til agenten",
                     "Sæt Bygges", "Send til runner", "Kommentér: agent startet"),
              ("Automatisk runner?", "Sæt Bygges (manuel)", 1),
              ("Sæt Bygges (manuel)", "Kommentér: start agenten selv")]
    return workflow("Fabrik 2 · Start opgave", noder, kanter)


# ------------------------------------------------------------------ 3: hent resultater

def wf_resultater():
    match = r"""
const status = $('Spørg runner').first().json;
const issues = $('Hent åbne issues').all().map(i => i.json).filter(i => i.number && !i.pull_request);
const efterNr = Object.fromEntries(issues.map(i => [i.number, i]));
const resultater = status.resultater || [];
const ud = [];
const min = (s) => Math.max(1, Math.round((s || 0) / 60));
const fod = (r) => `⏱️ ${min(r.varighed_sek)} min` +
  // Claude Code oplyser altid den beregnede API-pris; med abonnement betales den ikke.
  (r.pris_usd != null ? ` · 💰 ≈ $${Number(r.pris_usd).toFixed(2)} i API-pris (dækket af abonnement)` : '') +
  (r.antal_ture != null ? ` · 🔁 ${r.antal_ture} ture` : '');

for (const r of resultater) {
  const i = efterNr[r.issue];
  const filer = (r.filer || []).map(f => `- \`${f}\``).join('\n') || '- (ingen)';
  ud.push({ json: { ...r, fra_runner: true,
    labels_qa: labelsMed(i, 'Din QA'), labels_venter: labelsMed(i, 'Venter på dig'), labels_fast: labelsMed(i, 'Sidder fast'),
    pr_titel: `#${r.issue}: ${i?.title ?? r.branch}`,
    pr_krop: [`<!-- fabrik:pr -->`, `Closes #${r.issue}`, '', '## Hvad agenten har lavet', r.opsummering || '(ingen opsummering)', '',
              '## Tests', r.tests || '(ingen tests angivet)', '', '## Ændrede filer', filer, '', '---',
              `${fod(r)} · 🤖 Lavet af kodeagenten via softwarefabrikken. **Review før merge.**`].join('\n'),
    kommentar_faerdig: [`<!-- fabrik:faerdig -->`, `✅ **Agenten er færdig** – opgaven er flyttet til **Din QA**.`, '',
              r.opsummering || '', '', `**Tests:** ${r.tests || '(ingen angivet)'}`, '', fod(r)].join('\n'),
    kommentar_spoergsmaal: [`<!-- fabrik:spoergsmaal -->`, `❓ **Agenten har et spørgsmål**`, '',
              (r.spoergsmaal || '').split('\n').map(l => '> ' + l).join('\n'), '',
              `**Lavet indtil nu:** ${r.opsummering || '(intet)'}`, '',
              '_Svar i en kommentar. Så flytter fabrikken opgaven tilbage til **Godkendt**, og agenten starter igen med dit svar._'].join('\n'),
    kommentar_fast: [`<!-- fabrik:sidder-fast -->`, `🧱 **Agenten sidder fast**`, '', r.opsummering || '', '',
              r.log_hale ? `<details><summary>Sidste del af loggen</summary>\n\n\`\`\`\n${r.log_hale.replace(/```/g, "'''")}\n\`\`\`\n</details>\n` : '',
              fod(r), '',
              '_Flyt opgaven til **Godkendt** for at prøve igen (skriv gerne et hint i en kommentar), eller luk issuet for at droppe den._'].join('\n'),
  }});
}

// Issues der står som Bygges, men som runneren ikke kender (fx runneren var nede) -> Sidder fast.
const aktivNr = status.aktiv?.issue;
for (const i of issues) {
  const kendt = i.number === aktivNr || resultater.some(r => r.issue === i.number);
  const gammel = Date.now() - new Date(i.updated_at).getTime() > 3 * 60 * 1000;
  if (tilstandAf(i) === 'Bygges' && !kendt && gammel) {
    ud.push({ json: { issue: i.number, status: 'sidder_fast', fra_runner: false, labels_fast: labelsMed(i, 'Sidder fast'),
      kommentar_fast: '<!-- fabrik:sidder-fast -->\n🧱 **Sidder fast:** issuet står som Bygges, men runneren arbejder ikke på det ' +
        '(runneren var nede eller blev genstartet).\n\n_Flyt opgaven til **Godkendt** for at prøve igen, eller luk issuet._' } });
  }
}
return ud;
"""
    R = "$('Færdige').first().json"
    Q = "$('Spørgsmål').first().json"
    S = "$('Sidder fast').first().json"
    noder = [
        note("## 3 · Hent resultater fra runneren\n**Bygges → Din QA / Venter på dig / Sidder fast**\n\n"
             "Spørger runneren hvert minut. For hvert resultat:\n"
             "- **faerdig** → fabrikken åbner pull request, opgaven går til *Din QA*\n"
             "- **spoergsmaal** → spørgsmålet postes på issuet, *Venter på dig*\n"
             "- **sidder_fast** → fejl eller over 30 min, *Sidder fast*\n\n"
             "Til sidst kvitteres der, så runneren glemmer resultatet.", -40, -340, 560, 280),
        tidsplan(0, 0), manuel(0, 200),
        konfiguration(220, 100, dict(FELLES_KONFIG, runner_url="http://host.docker.internal:8765")),
        http("Spørg runner", 440, 100, "GET", "{{ " + K + ".runner_url }}/status", cred="runner"),
        http("Hent åbne issues", 660, 100, "GET", GH + "/issues", query=ISSUES_QUERY, **ALTID),
        kode("Match resultater", 880, 100, match),
        kode("Færdige", 1100, -60, "return $input.all().filter(x => x.json.status === 'faerdig').slice(0, 1);  // én ad gangen", medFaelles=False),
        http("Opret pull request", 1320, -60, "POST", GH + "/pulls",
             krop="{ title: " + R + ".pr_titel, head: " + R + ".branch, base: 'main', body: " + R + ".pr_krop }",
             onError="continueRegularOutput"),
        http("Kommentér: færdig", 1540, -60, "POST", GH + "/issues/{{ " + R + ".issue }}/comments",
             krop="{ body: " + R + ".kommentar_faerdig + ($json.html_url ? '\\n\\n🔗 Pull request: ' + $json.html_url : "
                  "'\\n\\n(Pull requesten fandtes allerede og er opdateret med de nye commits.)') }"),
        http("Sæt Din QA", 1760, -60, "PATCH", GH + "/issues/{{ " + R + ".issue }}", krop="{ labels: " + R + ".labels_qa }"),
        http("Kvittér færdig", 1980, -60, "POST", "{{ " + K + ".runner_url }}/resultater/{{ " + R + ".issue }}/kvitter",
             krop="{}", cred="runner"),
        kode("Spørgsmål", 1100, 120, "return $input.all().filter(x => x.json.status === 'spoergsmaal').slice(0, 1);  // én ad gangen", medFaelles=False),
        http("Post spørgsmål", 1320, 120, "POST", GH + "/issues/{{ " + Q + ".issue }}/comments",
             krop="{ body: " + Q + ".kommentar_spoergsmaal }"),
        http("Sæt Venter på dig", 1540, 120, "PATCH", GH + "/issues/{{ " + Q + ".issue }}",
             krop="{ labels: " + Q + ".labels_venter }"),
        http("Kvittér spørgsmål", 1760, 120, "POST", "{{ " + K + ".runner_url }}/resultater/{{ " + Q + ".issue }}/kvitter",
             krop="{}", cred="runner"),
        kode("Sidder fast", 1100, 300, "return $input.all().filter(x => x.json.status === 'sidder_fast').slice(0, 1);  // én ad gangen", medFaelles=False),
        http("Kommentér: sidder fast", 1320, 300, "POST", GH + "/issues/{{ " + S + ".issue }}/comments",
             krop="{ body: " + S + ".kommentar_fast }"),
        http("Sæt Sidder fast", 1540, 300, "PATCH", GH + "/issues/{{ " + S + ".issue }}",
             krop="{ labels: " + S + ".labels_fast }"),
        http("Kvittér sidder fast", 1760, 300, "POST",
             "{{ " + K + ".runner_url }}/resultater/{{ " + S + ".issue }}/kvitter", krop="{}", cred="runner"),
    ]
    kanter = [("Hvert minut", "Konfiguration"), ("Kør manuelt", "Konfiguration"),
              *kaede("Konfiguration", "Spørg runner", "Hent åbne issues", "Match resultater"),
              *kaede("Match resultater", "Færdige", "Opret pull request", "Kommentér: færdig", "Sæt Din QA", "Kvittér færdig"),
              *kaede("Match resultater", "Spørgsmål", "Post spørgsmål", "Sæt Venter på dig", "Kvittér spørgsmål"),
              *kaede("Match resultater", "Sidder fast", "Kommentér: sidder fast", "Sæt Sidder fast", "Kvittér sidder fast")]
    return workflow("Fabrik 3 · Hent resultater", noder, kanter)


# ------------------------------------------------------------------ 4: følg pull requests

def wf_pr():
    find = r"""
const prs = $('Hent pull requests').all().map(i => i.json).filter(p => p.number);
const issues = $('Hent alle issues').all().map(i => i.json).filter(i => i.number && !i.pull_request);
const efterNr = Object.fromEntries(issues.map(i => [i.number, i]));
const handlinger = {};
const set = new Set();
for (const p of prs) {                       // nyeste først: kun den nyeste PR pr. issue tæller
  const m = /^issue-(\d+)$/.exec(p.head?.ref || '');
  if (!m || set.has(Number(m[1]))) continue;
  set.add(Number(m[1]));
  const i = efterNr[Number(m[1])];
  if (!i) continue;
  const t = tilstandAf(i);
  if (p.merged_at) {
    if (t !== 'Færdig' || i.state === 'open')
      handlinger[i.number] = { i, ny: 'Færdig', luk: true, grund: 'completed',
        kommentar: `🎉 Pull request #${p.number} er merget. Opgaven er **Færdig**.` };
  } else if (p.state === 'closed') {
    if (t === 'Din QA')
      handlinger[i.number] = { i, ny: 'Færdig', luk: true, grund: 'not_planned',
        kommentar: `🗑️ Pull request #${p.number} blev lukket uden merge. Opgaven er droppet og markeret **Færdig**.` };
  } else if (t === 'Bygges' && !(p.body || '').includes('<!-- fabrik:pr')) {
    // Basic A: du (eller agenten i din session) har selv åbnet pull requesten.
    handlinger[i.number] = { i, ny: 'Din QA', luk: false,
      kommentar: `🔍 Pull request #${p.number} er åbnet. Opgaven er flyttet til **Din QA**.` };
  }
}
for (const i of issues) {
  const t = tilstandAf(i);
  if (i.state === 'closed' && t && t !== 'Færdig' && !handlinger[i.number])
    handlinger[i.number] = { i, ny: 'Færdig', luk: false, kommentar: '📦 Issuet er lukket. Opgaven er markeret **Færdig**.' };
}
return Object.values(handlinger).map(h => ({ json: {
  number: h.i.number, labels: labelsMed(h.i, h.ny),
  patch: h.luk && h.i.state === 'open'
    ? { labels: labelsMed(h.i, h.ny), state: 'closed', state_reason: h.grund }
    : { labels: labelsMed(h.i, h.ny) },
  kommentar: '<!-- fabrik:pr-status -->\n' + h.kommentar,
}}));
"""
    noder = [
        note("## 4 · Følg pull requests\n**Bygges → Din QA → Færdig**\n\n"
             "Branches hedder *issue-N*, så en pull request kan kobles til sin opgave.\n"
             "- PR merget → *Færdig* og issuet lukkes\n"
             "- PR lukket uden merge (mens opgaven er i Din QA) → droppet, *Færdig*\n"
             "- PR åbnet af dig selv (basic A) → *Din QA*\n"
             "- Issue lukket → *Færdig*\n\n"
             "Send tilbage: flyt issuet til *Godkendt* og skriv en kommentar på issuet. PR'en forbliver åben.",
             -40, -340, 600, 300),
        tidsplan(0, 0), manuel(0, 200),
        konfiguration(220, 100, dict(FELLES_KONFIG)),
        http("Hent pull requests", 440, 100, "GET", GH + "/pulls",
             query={"state": "all", "sort": "updated", "direction": "desc", "per_page": "50"},
             executeOnce=True, **ALTID),
        http("Hent alle issues", 660, 100, "GET", GH + "/issues",
             query={"state": "all", "sort": "updated", "direction": "desc", "per_page": "100"},
             executeOnce=True, **ALTID),
        kode("Find ændringer", 880, 100, find),
        http("Opdatér issue", 1100, 100, "PATCH", GH + "/issues/{{ $json.number }}", krop="$json.patch"),
        http("Kommentér status", 1320, 100, "POST",
             GH + "/issues/{{ $('Find ændringer').item.json.number }}/comments",
             krop="{ body: $('Find ændringer').item.json.kommentar }"),
    ]
    kanter = [("Hvert minut", "Konfiguration"), ("Kør manuelt", "Konfiguration"),
              *kaede("Konfiguration", "Hent pull requests", "Hent alle issues", "Find ændringer",
                     "Opdatér issue", "Kommentér status")]
    return workflow("Fabrik 4 · Følg pull requests", noder, kanter)


def main() -> None:
    UD.mkdir(parents=True, exist_ok=True)
    for filnavn, wf in [("1-forfin-opgave.json", wf_forfin()), ("2-start-opgave.json", wf_start()),
                        ("3-hent-resultater.json", wf_resultater()), ("4-foelg-pull-requests.json", wf_pr())]:
        (UD / filnavn).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"skrev n8n/workflows/{filnavn}  ({len(wf['nodes'])} noder)")


if __name__ == "__main__":
    main()
