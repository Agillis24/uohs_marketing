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

Najde nová rozhodnutí ÚOHS, vybere jedno nosné, přečte jeho plný text
a vyrobí hotový LinkedIn příspěvek plus texty slidů do Canvy. Nakonec
založí Issue jako archiv.

**Analýzu i psaní dělej sám, v této session.** Nedeleguj rozbor rozhodnutí
ani psaní textu na subagenty. Kvalita právního výkladu a čeština stojí a padají
s modelem, který to píše, a session model je pro tenhle úkol ten nejsilnější,
co je k dispozici. Subagent by běžel na slabším modelu a výsledek by byl znát.

---

## Step 0 — Příprava prostředí

Proběhne potichu, na nic se neptej.

**gh CLI.** Ověř `gh --version`. Když chybí, nainstaluj
`winget install --id GitHub.cli --silent --accept-package-agreements --accept-source-agreements`
a obnov PATH:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

**Přihlášení.** Ověř `gh auth status`. Když není přihlášeno, spusť
`gh auth login --web --git-protocol https` a řekni uživateli, že se otevře
prohlížeč a po přihlášení se má vrátit.

**Štítek.** `gh label create "tip-z-praxe" --repo Agillis24/uohs_marketing --color "6f42c1" 2>$null`
Chybu ignoruj, štítek nejspíš už existuje.

**pdftotext.** Ověř `Get-Command pdftotext`. Bývá v Git for Windows
(`C:\Program Files\Git\mingw64\bin\pdftotext.exe`). Když chybí, plný text PDF
nepůjde číst, což je zásadní omezení. Řekni to uživateli rovnou a navrhni
`winget install oschwartz10612.Poppler`, ať to má napříště.

---

## Step 1 — Seznam nových rozhodnutí

WebFetch na `https://uohs.gov.cz/cs/verejne-zakazky/sbirky-rozhodnuti.html?new=1`

Vytáhni všechny odkazy `/sbirky-rozhodnuti/detail-{ČÍSLO}.html` a poskládej
plné URL `https://uohs.gov.cz/cs/verejne-zakazky/sbirky-rozhodnuti/detail-{ČÍSLO}.html`

## Step 2 — Odfiltruj už zpracovaná

Přečti `C:\Users\pocit\uohs_marketing\processed_decisions.json` a vynech ID,
která tam jsou. Když soubor neexistuje, ber všechna nalezená jako nová.

## Step 3 — Metadata kandidátů

U každého nového rozhodnutí, nejvýš u deseti, načti detailní stránku
a vytáhni:

- **PDF URL** — `href` obsahující `/download/` nebo končící `.pdf`,
  relativní odkaz doplň o `https://uohs.gov.cz`
- **č. j.** — u „číslo jednací:"
- **sp. zn.** — u „spisová značka:"
- **datum** — u „nabytí pr. moci:"
- **instance** — „II." když stránka obsahuje „II. instance", jinak „I."
- **předmět** — nadpis `<h1>`

Instance kandidáta nevyřazuje, sbírej metadata u všech.

## Step 4 — Předvýběr, užší seznam

Ze shrnutí detailních stránek vyber 2 až 3 nejnadějnější kandidáty.
Tohle je jen hrubé síto, WebFetch vrací shrnutí od malého modelu a nedá se
o něj opřít při psaní. Slouží k tomu, aby se plný text nestahoval u všech
deseti zbytečně.

## Step 5 — Čím ses zabýval posledně

```powershell
gh issue list --repo Agillis24/uohs_marketing --label "tip-z-praxe" --state all --limit 5 --json title | ConvertFrom-Json
```

Zjisti témata posledních pěti příspěvků. Když užší seznam obsahuje kandidáta
na stejné úzké téma, je to důvod dát přednost jinému. Výjimka platí, když
rozhodnutí k tématu říká něco skutečně nového, tedy novou výjimku, obrat
v praxi nebo vyhraněnější skutkový stav. Pouhé zopakování stejného závěru
výjimka není.

Když příkaz selže, krok přeskoč.

## Step 6 — Plný text a finální výběr

U kandidátů z užšího seznamu stáhni PDF a převeď na text. Windows PowerShell 5.1
potřebuje obejít SSL, web ÚOHS má vadný certifikát:

```powershell
add-type @"
using System.Net; using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint s, X509Certificate c, WebRequest r, int p) { return true; }
}
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Invoke-WebRequest -Uri $pdfUrl -OutFile "$scratch\rozhodnuti.pdf" -UserAgent "Mozilla/5.0"
& pdftotext -layout -enc UTF-8 "$scratch\rozhodnuti.pdf" "$scratch\rozhodnuti.txt"
```

`$scratch` je scratchpad adresář této session. Výsledný `.txt` **přečti
nástrojem Read**, ať máš před sebou skutečný text rozhodnutí i s číslovanými
body odůvodnění, ne převyprávění. Na tomhle stojí jak správnost právních
závěrů, tak čísla bodů u slidů.

U hodně dlouhých rozhodnutí čti hlavně část s posouzením věci (viz Step 8),
zbytek stačí prolétnout kvůli kontextu.

**Výběr jednoho rozhodnutí.** Hledáš rozhodnutí zajímavé z hlediska rozhodovací
praxe. Zajímavé neznamená jen převratné. Kvalifikují se dvě různé věci:

- **Potvrzení zaběhnutého pravidla.** Rozhodnutí, které jasně a citovatelně
  zopakuje, jak se určitá věc dělá správně. Pro praxi je to cenné, protože
  dává oporu pro postup, o kterém lidé váhají.
- **Něco překvapivého, nového nebo prakticky užitečného.** Posun ve výkladu,
  nová výjimka, korekce prvního stupně, nezvyklý skutkový stav, ze kterého
  plyne poučení.

Žádné téma není předem upřednostněné. Kvalifikace, hodnocení, MNNC, změny
smluv, lhůty, rámcové dohody, poddodavatelé, rozsah přezkumu, dokazování,
zrušení zadávacího řízení, komunikace s dodavateli, všechno je ve hře.
První i druhá instance jsou si rovné, druhá instance je jen slabý bonus
za konečnost. Silné rozhodnutí prvního stupně na nosné téma ji přebije.

Vyhni se rozhodnutím čistě procesním nebo tak navázaným na konkrétní skutkový
stav, že z nich nic obecného neplyne.

## Step 7 — Text LinkedIn příspěvku

Kostra příspěvku:

```
🟣 Tip z praxe: [výstižný titulek, co je hlavní závěr]

🏛️ [Orgán] v rozhodnutí č. j. [čj.], sp. zn. [sp.zn.], ze dne [datum] [1–2 věty, výsledek řízení a o jakou zakázku šlo]

[Úvodní odstavec, viz pravidlo „Úvod" níže]

[2–4 odstavce, rozbor klíčových závěrů s konkrétním praktickým dopadem]

Z tohoto rozhodnutí podle nás plynou pro zadavatelskou praxi zejména:
📌 [závěr 1, konkrétní a zobecnitelný]
📌 [závěr 2]
📌 [závěr 3]
📌 [závěr 4, jen když je relevantní]

🔗 Rozhodnutí předsedy ÚOHS: [plná URL detailní stránky]

🤖 I s tímto rozhodnutím pracuje TENDERIX | První AI ve veřejných zakázkách při vyhledávání v rozhodovací praxi ÚOHS, judikatuře a právních předpisech pro veřejné zakázky.

hashtag#verejnezakazky hashtag#ZZVZ hashtag#UOHS [2–3 hashtagy k tématu] hashtag#TENDERIX
```

### Úvod, o co v rozhodnutí šlo

Čtenář musí hned na začátku vědět, do čeho jde. V úvodní části proto vždy
krátce představ:

- **O jakou zakázku šlo.** Ne obecně „veřejná zakázka", ale druh a předmět.
  Tedy zakázka na dodávky zdravotnické techniky, na služby spočívající
  ve zpracování projektové dokumentace, na stavební práce, jejichž předmětem
  byla nástavba budovy. Konkrétní předmět plnění pomáhá čtenáři odhadnout,
  jestli se ho to týká.
- **Co bylo předmětem sporu.** Čeho se navrhovatel domáhal nebo v čem úřad
  spatřoval pochybení.
- **Jaké z toho plynou závěry pro praxi.** Naznač to už v úvodu, ať čtenář ví,
  proč má číst dál. Rozvedeš to pak v 📌 bodech.

Tyhle tři věci můžou být rozložené mezi odstavec s označením rozhodnutí
a úvodní odstavec, nemusí být v jednom bloku. Podstatné je, že po prvních
dvou odstavcích čtenář ví, o jakou zakázku šlo, o co se vedl spor a proč
ho to má zajímat.

### Závěr příspěvku

Příspěvek vždy končí odkazem na rozhodnutí a podpisem. Podpis se cituje
doslova, nepřepisuj ho:

```
🤖 I s tímto rozhodnutím pracuje TENDERIX | První AI ve veřejných zakázkách při vyhledávání v rozhodovací praxi ÚOHS, judikatuře a právních předpisech pro veřejné zakázky.
```

Za podpisem následují už jen hashtagy.

### Emoji

Používej je s rozvahou a citem. Drž se ustálené kostry, tedy 🟣 na začátku,
🏛️ u označení rozhodnutí, 📌 u závěrů, 🔗 u odkazu a 🤖 u podpisu. Nic dalšího
nepřidávej. Žádné emoji uvnitř odstavců, žádné ozdoby u hashtagů, nic
na zdůraznění jednotlivých slov. Když má příspěvek méně závěrů, klesne počet
📌 a to je v pořádku. Příspěvek má působit jako odborný text, ne jako reklama.

### Styl, piš jako člověk

U textu pod značkou je to zásadní. Když text vypadá vygenerovaně, čtenář
začne pochybovat i o právních závěrech v něm.

- Pomlčky, dvojtečky a středníky používej minimálně. Radši dvě krátké věty
  než jedno souvětí slepené pomlčkou uprostřed.
- Dvojtečku jen tam, kde opravdu uvozuje výčet nebo citaci, ne jako univerzální
  spojku mezi dvěma myšlenkami.
- Středník skoro nikdy, v češtině působí knižně.
- Pomlčku nech na vsuvky, které tam vážně patří, ne do každého odstavce.
- Platí to i pro 📌 závěry a texty slidů, ne jen pro hlavní odstavce.
- Po dopsání draftu si pomlčky spočítej. Víc než dvě nebo tři na celý
  příspěvek znamenají přepis dotčených vět.

### Délka

Cíl je 2500 až 3000 znaků, protože LinkedIn nad 3000 příspěvek nepřijme.
Bezpečné pásmo je 2700 až 2900, ať drobná úprava při vkládání limit nepřekročí.

Délku po dopsání skutečně změř, neodhaduj:
```powershell
(Get-Content "$scratch\prispevek.txt" -Raw -Encoding UTF8).Length
```

Když je text pod 2500, rozveď jádro sporu nebo rozbor o věcný obsah,
konkrétnější dopad, ne vatu. Když přeleze 3000, krať prostřední odstavce
rozboru. Úvod ani 📌 body nekrať, ty nesou hlavní hodnotu.

### Anonymizace

Neuváděj názvy zadavatele, dodavatele, navrhovatele ani dalších účastníků,
ledaže je identita nutná pro pochopení závěru, což bývá výjimečně, například
u zvláštního typu zadavatele. Používej „zadavatel", „vybraný dodavatel",
„navrhovatel", „stěžovatel". Čtenář se má v situaci poznat, ne sledovat spor
konkrétních firem.

Druh a předmět zakázky podle pravidla „Úvod" se popisuje obecně a s anonymizací
nekoliduje. Tedy „zakázka na stavební práce spočívající v nástavbě mateřské
školy", nikoli název obce.

## Step 8 — Texty slidů do Canvy

Vytáhni 3 až 6 nosných závěrů, každý jako jeden slide:

```
### Slide N

[2–5 vět. Klíčový závěr, zobecnitelný pro praxi.
**Nejdůležitější části tučně** a zbytek normálně.]

*Rozhodnutí předsedy ÚOHS č. j. [čj.], sp. zn.: [sp.zn.] ze dne [datum]:*

> 📎 Zdroj: bod [N] odůvodnění
```

Dobrý slide je úderný a soběstačný. Čtenář, který uvidí jen jeho, musí
právnímu bodu rozumět bez čtení celého rozhodnutí.

### Odkud brát obsah slidů

Citace a závěry ber **z části, kde věc posuzuje nebo se k ní vyjadřuje úřad
či předseda úřadu**, tedy z vlastního právního hodnocení orgánu. Jen to je
citovatelné jako závěr rozhodovací praxe.

Názvy těch částí se rozhodnutí od rozhodnutí liší, neřiď se seznamem, ale tím,
čí názor se v dané pasáži podává. Běžně narazíš na **„Stanovisko předsedy
Úřadu"**, **„K námitkám rozkladu"**, **„Posouzení věci Úřadem"**, **„Právní
posouzení"**, **„Závěry Úřadu"**, **„Závěr"** a řadu podobných variant včetně
podnadpisů typu „K otázce…". Rozhodující je, že tam mluví orgán sám za sebe.

Naopak **nikdy necituj jako závěr úřadu** pasáže, které jen reprodukují tvrzení
stran, tedy „Rozklad obviněného", „Námitky rozkladu", „Návrh navrhovatele",
„Vyjádření zadavatele" a podobně. Úřad je často následně vyvrací. Vydávat
je za závěr rozhodovací praxe by byla věcná chyba a u příspěvku pod značkou
i reputační problém.

Pozor i na pasáže uvnitř hodnotící části, kde úřad cituje argument strany,
aby se s ním vypořádal. Poznáš je podle uvozovacích obratů typu „navrhovatel
namítá, že", „obviněný tvrdí". Závěr je až to, co na to úřad říká.

Když si u konkrétní věty nejsi jistý, čí je to názor, dohledej v textu,
kdo mluví, a raději ji nepoužij, než abys ji přisoudil úřadu.

### Číslo bodu odůvodnění

Pod citaci vždy doplň `> 📎 Zdroj: bod N odůvodnění` s číslem bodu, ze kterého
závěr vychází, případně rozsahem, tedy „body 53, 57 a 62". Slouží ke zpětné
kontrole, uživatel si podle toho tvrzení ověří přímo v PDF.

- Řádek je záměrně mimo text slidu a do Canvy se nekopíruje. Když má být číslo
  vidět i na slidu, uživatel si ho do citace doplní sám.
- Čísla ber výhradně z plného textu PDF, kde jsou číslované odstavce odůvodnění.
  Nikdy ne z WebFetch shrnutí, ta čísla bodů spolehlivě neuvádějí.
- Když se PDF nepodařilo přečíst a čísla bodů neznáš, napiš to výslovně místo
  odhadu. Nesprávné číslo je horší než žádné.
- Totéž je vhodné i u 📌 závěrů, pokud vycházejí z jiných bodů než slidy.

## Step 9 — Výstup do konverzace

Vypiš výsledek v tomhle členění:

---
📝 **TEXT LINKEDIN PŘÍSPĚVKU**
*(připraveno ke zkopírování)*

[celý příspěvek]

*Délka: N znaků*

---
🖼️ **TEXTY PRO CANVA SLIDES**
*(zkopírujte každý slide do šablony, tučné části zvýrazněte)*

[slidy]

---

## Step 10 — Založ Issue

Obsah je stejný jako ve Step 9. Text **nevkládej přímo do příkazu**, ani
do PowerShell heredocu. Uvozovky, `$` a zpětná lomítka v textu by se rozbily.

Napiš tělo Issue nástrojem Write do `$scratch\issue_body.md` a pak:

```powershell
$title = "Tip z praxe — $(Get-Date -Format 'dd.MM.yyyy') — [předmět, max 60 znaků]"
gh issue create --repo Agillis24/uohs_marketing --title $title --label "tip-z-praxe" --body-file "$scratch\issue_body.md"
```

Tělo Issue obsahuje tabulku s metadaty rozhodnutí, celý text příspěvku
v bloku kódu, všechny slidy a odkaz na detail na webu ÚOHS.

Po založení vypiš uživateli URL Issue.

## Step 11 — Zapiš zpracované rozhodnutí

Do `C:\Users\pocit\uohs_marketing\processed_decisions.json` přidej ID vybraného
rozhodnutí. Soubor uprav nástrojem Edit nebo Write, ne přes PowerShell
`ConvertTo-Json`. Ten u jednoprvkového pole vyrobí skalár místo pole a soubor
tím rozbije.

Zapisuj jen ID rozhodnutí, o kterém jsi psal. Kandidáty, které jsi zvážil
a nepoužil, nech nezapsané, ať můžou vyjít příště.

---

## Když něco selže

- **gh chybí nebo instalace selže** — řekni to, výstup ukaž, Issue přeskoč
- **gh není přihlášen** — poproš o `gh auth login`, pak zkus znovu
- **pdftotext chybí** — řekni to výslovně, pokračuj přes WebFetch shrnutí
  a u slidů uveď, že čísla bodů nejsou k dispozici
- **web ÚOHS nedostupný** — řekni to a skonči
- **žádná nová rozhodnutí** — řekni to a skonči
- **PDF se nepodaří stáhnout u všech kandidátů** — zkus WebFetch shrnutí,
  a když ani to ne, skonči
- **založení Issue selže** — výstup stejně ukaž, vypiš chybu a pokračuj
