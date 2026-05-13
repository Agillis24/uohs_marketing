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
procurement practitioners, produces a ready-to-publish LinkedIn post with
Canva slide texts, and creates a GitHub Issue archive — all automatically.

---

## Step 0 — Setup check (run before anything else)

Before starting the analysis, silently verify that GitHub CLI is available
and authenticated. Do this in the background without asking the user anything.

### 0a — Check if gh CLI is installed

```powershell
gh --version 2>$null
```

If the command fails (exit code != 0), install it automatically:

```powershell
winget install --id GitHub.cli --silent --accept-package-agreements --accept-source-agreements
```

Wait for installation to complete, then refresh the PATH:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### 0b — Check if gh CLI is authenticated

```powershell
gh auth status 2>$null
```

If not authenticated (exit code != 0), run interactive login:
```powershell
gh auth login --web --git-protocol https
```

This opens a browser window for GitHub authentication. Tell the user:
"Otevře se prohlížeč pro přihlášení k GitHubu — po přihlášení se sem vraťte
a analýza pokračuje automaticky." Wait for the command to complete.

### 0c — Ensure the label exists in the repo

```powershell
gh label create "tip-z-praxe" --repo Agillis24/uohs_marketing --color "6f42c1" --description "Tip z praxe LinkedIn post" 2>$null
```

Ignore any error here (label may already exist).

---

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
page to extract the full case summary, legal findings, and conclusions.
The ÚOHS detail pages contain rich structured summaries of the legal reasoning.

Optionally attempt full PDF download for richer text (Windows PowerShell 5.1
requires SSL bypass):

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

Then use `anthropic-skills:pdf` to read it. If PDF reading fails, WebFetch
summaries are sufficient — proceed with those.

## Step 5 — Select the best decision

Apply your legal knowledge to select the ONE decision most worth writing about:

- **Generalizable conclusions** — principles applicable across many procurement
  situations, not just the specific case facts
- **Practical impact** — rules that zadavatelé or dodavatelé can act on
- **Key themes**: qualification requirements, evaluation criteria, transparency
  of selection reports, MNNC, contract modifications, procedural deadlines

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

Write in professional Czech. Tone: authoritative but accessible — senior
procurement lawyer explaining to a colleague.

## Step 7 — Generate Canva slide texts

Extract 3–6 key conclusions as slide quotes. Each slide:

```
### Slide N

[2–5 vět. Klíčový závěr, zobecnitelný pro praxi.
**Nejdůležitější části věty tučně** a zbytek normálně.]

*Rozhodnutí předsedy ÚOHS č. j. [čj.], sp. zn.: [sp.zn.] ze dne [datum]:*
```

Good slides are punchy and self-contained — a reader seeing only this slide
understands the legal point without reading the full decision.

## Step 8 — Display output in conversation

Show the results with these exact sections:

---
📝 **TEXT LINKEDIN PŘÍSPĚVKU**
*(připraveno ke zkopírování)*

[the full post]

---
🖼️ **TEXTY PRO CANVA SLIDES**
*(zkopírujte každý slide do šablony v Canvě — tučné části zvýrazněte)*

[slides]

---

## Step 9 — Create GitHub Issue

Create the Issue using the content already displayed in Step 8. Build the
body as a heredoc and pass it to gh:

```powershell
$date = Get-Date -Format 'dd.MM.yyyy'
$subject = "[předmět rozhodnutí, max 60 znaků]"
$title = "Tip z praxe — $date — $subject"

$issueBody = @"
## 📝 TEXT LINKEDIN PŘÍSPĚVKU

``````
[sem vložte celý LinkedIn text z Step 6]
``````

---

## 🖼️ TEXTY PRO CANVA SLIDES

[sem vložte všechny slides z Step 7 ve formátu markdown]

---
_Vygenerováno: $date — manuální spuštění v Claude Code_
"@

$issueBody | gh issue create --repo Agillis24/uohs_marketing --title $title --label "tip-z-praxe" --body-file -
```

After creating, print the Issue URL to the user so they can open it if needed.

## Step 10 — Update processed decisions

Update `C:\Users\pocit\uohs_marketing\processed_decisions.json` with the ID
of the selected decision:

```powershell
$file = "C:\Users\pocit\uohs_marketing\processed_decisions.json"
if (Test-Path $file) {
    $ids = Get-Content $file | ConvertFrom-Json
    if ($ids -notcontains "[DECISION_ID]") {
        $ids += "[DECISION_ID]"
        $ids | ConvertTo-Json | Set-Content $file -Encoding UTF8
    }
}
```

---

## Error handling

- **gh not installed / install fails**: inform user, show output, skip Issue
- **gh auth fails**: ask user to run `gh auth login` once, then retry
- **ÚOHS website unreachable**: inform the user and stop
- **No new decisions**: tell the user, stop
- **All content fetches fail**: tell the user, stop
- **Issue creation fails**: show output anyway, print error, continue
