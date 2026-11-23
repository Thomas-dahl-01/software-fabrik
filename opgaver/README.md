# Opgaveidéer

Grove idéer, klar til at blive oprettet som issues med labelen **Idé**. De skal være korte, fordi AI-trinnet forfiner dem. Kopiér titel og tekst ind i et nyt issue. Opret dem i rækkefølge, fordi de senere opgaver bygger på de tidligere.

## Produkt: Football Team Manager

1. **Opret spillere**
   > Jeg vil kunne oprette spillere med navn, trøjenummer og position og se en liste over holdet i terminalen.

2. **Registrér kampe og resultater**
   > Registrér en kamp med dato, modstander, hjemme/ude og resultat. Vis en liste over kampe.

3. **Mål og assists**
   > Registrér hvem der scorede og hvem der lavede assist i en kamp.

4. **Spillerstatistik**
   > Vis statistik pr. spiller: kampe, mål, assists. Og en topscorerliste.

5. **Træninger**
   > Planlæg træninger og registrér hvem der mødte op. Vis fremmøde pr. spiller.

### Til at teste de svære veje
- **Bevidst uklar:** "Lav en holdopstilling", så agenten eller AI'en forhåbentlig spørger (hvilken formation? kun spillere der er mødt til træning?).
- **For stor:** "Lav en hel sæsonplanlægning med turneringer, tabeller og skader", så AI'en bør foreslå at dele den op.

## Fabrikken selv (byg fabrikken med fabrikken)

6. **Bedre fejlbesked når Ollama ikke svarer**
   > Hvis AI-trinnet fejler, skal issuet ikke hænge i Forfines. Skriv en kommentar med fejlen og sæt det tilbage til Idé.

7. **Evalueringsrapport fra kørselsloggen**
   > Et script der læser runner/logs/koersler.jsonl og skriver en markdown-tabel med alle kørsler: issue, status, varighed, pris, antal ture.

8. **Statusside i runneren**
   > Runneren skal have en simpel HTML-side på `/` der viser aktiv opgave og de seneste kørsler.
