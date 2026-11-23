# Specifikationsskabelon

Din grove idé i **Idé** må være kort. AI-trinnet i n8n (workflow 1) omskriver den til denne faste skabelon, så kodeagenten altid får de samme oplysninger. Skabelonen er en del af prompten i [`n8n/prompts/forfining.md`](../n8n/prompts/forfining.md).

| Felt | Indhold | Hvorfor feltet findes |
|---|---|---|
| **Titel** | Kort, i bydeform | Bliver PR-titlen. Bydeform tvinger en konkret handling frem |
| **Mål** | Hvad der skal bygges (1-3 sætninger) | Agentens hovedopgave i én sætning |
| **Hvorfor** | Problemet for brugeren | Giver agenten mulighed for at træffe små valg i ånden af opgaven |
| **Omfang** | Ting der SKAL laves | Gør opgaven afgrænset |
| **Uden for omfang** | Ting der IKKE skal laves | Kodeagenter har en tendens til at "hjælpe" med ekstra funktioner. Det her bremser det og holder PR'en lille og let at reviewe |
| **Begrænsninger** | Sprog, mapper, afhængigheder, filer der ikke må røres | Sikkerhed og konsistens. Fx "kun filer i `produkt/`" |
| **Acceptkriterier** | Testbare, gerne *Givet / når / så*, som tjekliste | Bliver både agentens definition of done og din QA-tjekliste i PR'en |
| **Tests** | Hvilke automatiske tests der skal skrives og køres | Tests er det, der gør review af en agents arbejde realistisk |
| **Område i repoet** | Forventede filer/mapper | Hjælper agenten med at finde rundt, og dig med at opdage, hvis PR'en rører noget uventet |
| **Antagelser** | Små valg AI'en har truffet | Gør skjulte gæt synlige, så du kan rette dem før godkendelse |
| **Spørgsmål til dig** | Ting der skal afklares | AI'en må ikke gætte på ting, der ændrer resultatet |
| **Vurdering** | Størrelse (S/M/L), risiko, anbefaling | AI'en rådgiver om opgaven er klar, men du beslutter |

## Designvalg

- **JSON i stedet for fri tekst.** Ollama kaldes med `format: "json"`, og n8n bygger selv markdown-kommentaren. Det gør output stabilt også med en mindre lokal model, og et manglende felt bliver til "(ingen)" i stedet for at ødelægge formatet.
- **Lille opgave.** Prompten kræver, at opgaven kan bygges på under 30 minutter (runnerens timeout). Store idéer foreslås delt op.
- **Samtalen tæller.** Når du kommenterer, sendes hele samtalen med igen, og dine nyeste kommentarer vejer tungest. Forfiningen er en dialog, ikke et engangskald.
- **Rådgiver, ikke godkender.** Vurderingen er en anbefaling. Labelen `Godkendt` sættes kun af dig.

## Eksempel

**Grov idé (issue):**
> Tilføj udgifter
> Jeg vil kunne skrive en udgift ind med beløb og kategori

**AI-trinnets output (kommentar på issuet):** *indsæt et rigtigt output her, når den første opgave er kørt igennem (link til issuet).*
