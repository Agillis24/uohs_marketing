---
name: uohs
description: >
  TENDERIX workflow: analyze new ÚOHS public procurement decisions and generate
  a LinkedIn "Tip z praxe" post (text + Canva slide quotes). Use this skill
  whenever the user types /uohs, asks to "zpracuj ÚOHS", "připrav příspěvek
  z ÚOHS", "nová rozhodnutí ÚOHS", or anything about analyzing ÚOHS decisions
  for LinkedIn. Always invoke this skill for these requests — do not attempt
  to handle them ad hoc.
---

# ÚOHS → TENDERIX LinkedIn Post Generator

This skill fetches new ÚOHS decisions, selects the most interesting one for
procurement practitioners, and produces a ready-to-publish LinkedIn post with
Canva slide texts. It then creates a GitHub Issue as an archive.

## Step 1 — Fetch the list of new decisions

Use WebFetch on:
`https://uohs.gov.cz/cs/verejne-zakazky/sbirky-rozhodnuti.html?new=1`

Extract every link matching `/sbirky-rozhodnuti/detail-{NUMBER}.html`.
Build full URLs: `https://uohs.gov.cz/cs/verejne-zakazky/sbirky-rozhodnuti/detail-{NUMBER}.html`

## Step 2 — Check which decisions are new

Read `C:\Users\pocit\uohs_marketing\processed_decisions.json`.
If the file doesn't exist, treat all found decisions as new.
Skip any IDs already in the file.

## Step 3 — Fetch detail pages and collect metadata

For each new decision (up to 10, newest first), use WebFetch on the detail URL.
Extract:
- **PDF URL**: any `href` containing `/download/` or ending in `.pdf`
  → prepend `https://uohs.gov.cz` if relative
- **č.j.** (číslo jednací): text near "číslo jednací:" 
- **sp.zn.** (spisová značka): text near "spisová značka:"
- **datum**: text near "nabytí pr. moci:"
- **instance**: "II." if page contains "II. instance", otherwise "I."
- **předmět**: the `<h1>` heading text

Prioritize II. instance decisions (předseda ÚOHS) — they tend to have richer,
more generalizable legal conclusions.

## Step 4 — Get decision content

For each promising decision (prefer II. instance), use WebFetch on the detail
page URL to extract the full case summary, legal findings, and conclusions.
The ÚOHS detail pages contain rich structured summaries of the legal reasoning.

If the WebFetch summary seems insufficient for a given decision, try fetching
additional subpages linked from the detail page.

Note: Full PDF text extraction requires Python+pdfplumber or pdftoppm installed
locally. If available, download the PDF using PowerShell (with SSL bypass for
Windows PowerShell 5.1):

```powershell
add-type @"
using System.Net; using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint s, X509Certificate c, WebRequest r, int p) { return true; }
}
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $pdfUrl -OutFile "$env:TEMP\uohs.pdf" -UserAgent "Mozilla/5.0"
```

Then use `anthropic-skills:pdf` to read it. If PDF reading fails, proceed with
WebFetch summaries — they are usually sufficient for the analysis.

## Step 5 — Select the best decision

Read all extracted texts and apply your legal knowledge to select the ONE
decision most worth writing about. Look for:

- **Generalizable conclusions** — principles applicable across many procurement
  situations, not just the specific case facts
- **Practical impact** — rules that zadavatelé or dodavatelé can act on
- **Key themes**: qualification requirements, evaluation criteria, transparency
  of selection reports, MNNC (mimořádně nízká nabídková cena), contract
  modifications, procedural deadlines, scope of review

Avoid decisions that are purely procedural or fact-specific with no broader lesson.

## Step 6 — Generate the LinkedIn post

Follow this template EXACTLY (spacing, emojis, hashtag format):

```
🟣 Tip z praxe: [výstižný titulek — co je hlavní závěr]

🏛️ [Orgán] v rozhodnutí č. j. [čj.], sp. zn. [sp.zn.], ze dne [datum] [1–2 věty: výsledek řízení a předmět zakázky]

[Odstavec: jádro sporu — co bylo předmětem přezkumu, 3–5 vět]

[2–4 odstavce: rozbor klíčových závěrů s konkrétními praktickými dopady pro zadavatele/dodavatele. Piš přirozeně, odborně, ale srozumitelně.]

Z tohoto rozhodnutí podle nás plynou pro zadavatelskou praxi zejména:
📌 [závěr 1 — konkrétní, zobecnitelný]
📌 [závěr 2]
📌 [závěr 3]
📌 [závěr 4, pouze pokud je relevantní]

🔗 Rozhodnutí předsedy ÚOHS: [plná URL detailní stránky]

🤖 I s tímto rozhodnutím pracuje TENDERIX | První AI ve veřejných zakázkách při vyhledávání v rozhodovací praxi ÚOHS, judikatuře a právních předpisech pro veřejné zakázky.

hashtag#verejnezakazky hashtag#ZZVZ hashtag#UOHS [2–3 hashtagy k tématu, bez mezery za #] hashtag#TENDERIX
```

Language note: Write in professional Czech. The tone is authoritative but
accessible — think senior procurement lawyer explaining to a colleague.

## Step 7 — Generate Canva slide texts

Extract 3–6 key conclusions as slide quotes. Each slide:

```
### Slide N

[2–5 vět. Klíčový závěr, zobecnitelný pro praxi. 
**Nejdůležitější části věty tučně** a zbytek normálně.]

*Rozhodnutí předsedy ÚOHS č. j. [čj.], sp. zn.: [sp.zn.] ze dne [datum]:*
```

Good slides are punchy and self-contained — a reader who sees only this slide
understands the legal point without reading the full decision.

## Step 8 — Display output in conversation

Show the results clearly with these sections:

---
📝 **TEXT LINKEDIN PŘÍSPĚVKU**
*(připraveno ke zkopírování)*

[the full post]

---
🖼️ **TEXTY PRO CANVA SLIDES**
*(zkopírujte každý slide do šablony v Canvě — tučné části zvýrazněte)*

[slides]

---

## Step 9 — Update processed decisions (optional)

If the local repo exists at `C:\Users\pocit\uohs_marketing\`, update
`processed_decisions.json` so the same decision isn't picked next time:

```powershell
# Read, add new ID, write back
$file = "C:\Users\pocit\uohs_marketing\processed_decisions.json"
if (Test-Path $file) {
    $ids = Get-Content $file | ConvertFrom-Json
    $ids += "[DECISION_ID]"
    $ids | ConvertTo-Json | Set-Content $file
}
```

This is optional — if the file isn't present on this device, the next run
will simply re-evaluate recent decisions and pick the best one again.

## Error handling

- If ÚOHS website is unreachable: inform the user and stop
- If all PDFs fail to download: try WebFetch on the detail pages to get partial
  text, and proceed with what's available
- If GitHub Issue creation fails: show the content here anyway and ask the user
  to create the issue manually
- If no new decisions found: tell the user and stop
