# Football Team Manager

Det produkt, softwarefabrikken bygger: et administrationssystem til et fodboldhold i terminalen. Alt i denne mappe er lavet af kodeagenten via issues og pull requests (undtagen denne README og `tests/conftest.py`).

## Funktioner (bygges én opgave ad gangen)
1. Opret spillere
2. Registrér kampe og resultater
3. Hold styr på mål og assists
4. Lav spillerstatistikker
5. Administrér træninger

## Arkitektur (fast, så alle opgaver passer sammen)

```
produkt/
├── fodbold/              Python-pakken
│   ├── __init__.py
│   ├── __main__.py       gør "python -m fodbold" muligt (kalder cli.main)
│   ├── db.py             SQLite-forbindelse og oprettelse af tabeller
│   ├── spillere.py       én fil pr. område med rene funktioner
│   ├── kampe.py
│   ├── ...
│   └── cli.py            kommandolinje (argparse) med én underkommando pr. område
├── tests/                pytest, én testfil pr. modul
└── data/hold.db          databasen (oprettes automatisk, ikke i git)
```

**Konventioner:**
- Python 3.12+, kun standardbiblioteket (`sqlite3`, `argparse`, `datetime`) plus `pytest` til tests.
- Logik ligger i modulerne som funktioner, der tager en `sqlite3.Connection` som første argument. `cli.py` gør kun to ting: læser argumenter og printer resultater. Så kan al logik testes uden terminalen.
- `db.forbind(sti=None)` åbner databasen. Standardstien er `produkt/data/hold.db`, og miljøvariablen `FODBOLD_DB` overskriver den. Tests bruger `":memory:"`.
- Hvert modul opretter selv sine tabeller via en funktion, som `db.py` kalder, og bruger `CREATE TABLE IF NOT EXISTS`.
- Navne på funktioner og tabeller skrives på dansk uden æøå (fx `opret_spiller`, `traeninger`).
- Datoer gemmes som tekst i ISO-format (`2026-11-23`).

## Kør
```powershell
cd produkt
python -m fodbold --help
python -m pytest
```
