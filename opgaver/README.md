# Opgaveidéer

Grove idéer, klar til at blive oprettet som issues med labelen **Idé**. Skriv dem kort, for AI-trinnet forfiner dem. Kopiér titel og tekst ind i et nyt issue.

## Produkt: personlig finance tracker

1. **Datamodel og database for posteringer**
   > Lav en SQLite-database med posteringer: dato, beløb, beskrivelse, kategori. Indtægter er positive, udgifter negative. Skal have funktioner til at tilføje og hente posteringer.

2. **CLI: tilføj og vis posteringer**
   > Jeg vil kunne skrive `python -m produkt tilfoej -120.50 mad "Netto"` og `python -m produkt vis` i terminalen.

3. **Månedsoversigt pr. kategori**
   > Vis en oversigt for en måned: hvor meget er brugt pr. kategori, og hvad er balancen.

4. **Budgetter**
   > Jeg vil kunne sætte et månedligt budget pr. kategori og se, om jeg er over.

5. **Import fra bank-CSV**
   > Importér posteringer fra en CSV-fil fra banken (dato;tekst;beløb, dansk format med komma som decimaltegn).

6. **Eksport til CSV**
   > Eksportér posteringer for en periode til CSV.

## Fabrikken selv (byg fabrikken med fabrikken)

7. **Statusside i runneren**
   > Runneren skal have en simpel HTML-side på `/` der viser aktiv opgave og de seneste kørsler fra koersler.jsonl.

8. **Evalueringsrapport fra kørselsloggen**
   > Et script der læser runner/logs/koersler.jsonl og skriver en markdown-tabel med alle kørsler: issue, status, varighed, pris, antal ture.

9. **Bedre fejlbesked når Ollama ikke svarer**
   > Hvis AI-trinnet fejler, skal issuet ikke hænge i Forfines. Skriv en kommentar med fejlen og sæt det tilbage til Idé.
