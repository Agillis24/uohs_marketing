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
a vyrobí hotový LinkedIn příspěvek, text prvního komentáře a carousel
v Canvě. Nakonec založí Issue jako archiv.

**Analýzu i psaní dělej sám, v této session.** Nedeleguj rozbor rozhodnutí
ani psaní textu na subagenty. Kvalita právního výkladu a čeština stojí a padají
s modelem, který to píše, a session model je pro tenhle úkol ten nejsilnější,
co je k dispozici. Subagent by běžel na slabším modelu a výsledek by byl znát.

## Věcná správnost je nadřazená všemu ostatnímu

Tenhle příspěvek vychází pod značkou a čtou ho lidé, kteří podle něj budou
zadávat veřejné zakázky. Jedna vymyšlená věta je horší než deset nudných.
Když si musíš vybrat mezi poutavým a přesným, vyber přesné.

- **Nevymýšlej si.** Každý skutkový i právní údaj musí mít oporu v textu
  rozhodnutí. Když v něm něco není, do příspěvku to nepatří, ani kdyby to
  z tvé znalosti práva vyplývalo a znělo rozumně.
- **Nezkresluj.** Netvrď víc, než rozhodnutí říká, a netvrď to důrazněji.
  Závěr vázaný na konkrétní okolnosti nedělej obecným pravidlem. Z „úřad
  v této věci neshledal pochybení" nedělej „takový postup je v pořádku".
- **Nepřisuzuj úřadu cizí názory.** Argument účastníka není závěr úřadu,
  i když je v rozhodnutí odcitovaný. Viz Step 8.
- **Nedoplňuj kontext z hlavy.** Nepřidávej odkazy na judikaturu, jiná
  rozhodnutí ani na znění zákona, které v rozhodnutí nezazněly. Když by
  odkaz text zpřesnil, ale v rozhodnutí není, vynech ho.
- **Když si nejsi jistý, tvrzení vypusť.** Kratší a jistý příspěvek je lepší
  než delší s jedním sporným bodem.

Hotový draft se povinně prožene zpětnou kontrolou, viz Step 9. Bez ní se
příspěvek uživateli nepředkládá.

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
🟣 Tip z praxe: [hák, praktická sázka pro čtenáře]

[Úvodní odstavec, o jakou zakázku šlo a co bylo předmětem sporu, viz pravidlo „Úvod" níže]

[2–4 odstavce, rozbor klíčových závěrů s konkrétním praktickým dopadem]

Z tohoto rozhodnutí podle nás plynou pro zadavatelskou praxi zejména:
📌 [závěr 1, konkrétní a zobecnitelný]
📌 [závěr 2]
📌 [závěr 3]
📌 [závěr 4, jen když je relevantní]

🏛️ [Orgán], č. j. [čj.], sp. zn. [sp.zn.], ze dne [datum]. Odkaz na rozhodnutí v prvním komentáři.

🤖 I s tímto rozhodnutím pracuje TENDERIX | První AI ve veřejných zakázkách při vyhledávání v rozhodovací praxi ÚOHS, judikatuře a právních předpisech pro veřejné zakázky.

#verejnezakazky #ZZVZ #UOHS [2–3 hashtagy k tématu] #TENDERIX
```

Hashtagy piš normálně s mřížkou. Dřívější verze šablony měla `hashtag#...`,
což je artefakt kopírování textu z LinkedInu ven. Po vložení zpátky by se
vypsal doslova a hashtag by z toho nevznikl.

### První dva řádky rozhodují

LinkedIn na mobilu ukáže zhruba prvních 140 až 200 znaků a zbytek schová
pod „zobrazit více". Co je nad tím zlomem, rozhoduje, jestli někdo čte dál.

Do prvních dvou řádků proto nikdy nedávej spisové značky ani číslo jednací.
Pro čtenáře je to bariéra, ne informace, a spotřebuje to celý viditelný
prostor. Formální označení rozhodnutí patří až dolů, k podpisu.

Nahoru patří **praktická sázka**, tedy co čtenář riskuje nebo získá. Otázka,
kterou si zadavatel sám klade, nebo tvrzení, které je proti běžnému očekávání.
Nadsazovat ale nemusíš, publikum jsou profesionálové a klikbajt je odradí.
Stačí konkrétnost.

- Slabé: „Tip z praxe: k oznámení o výběru a jeho náležitostem"
- Silné: „Tip z praxe: musí zadavatel do oznámení o výběru opsat celé životopisy?"

### Odkaz patří do prvního komentáře

Do těla příspěvku odkaz na rozhodnutí **nedávej**. LinkedIn upozaďuje
příspěvky, které vedou pryč z platformy, a dosah tím znatelně klesá.
V příspěvku zůstane jen věta, že odkaz je v prvním komentáři.

Odkaz vypiš zvlášť jako text prvního komentáře, viz Step 10:

```
🔗 Rozhodnutí [orgán]: [plná URL detailní stránky]
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

Tyhle tři věci můžou být rozložené mezi hák a úvodní odstavec, nemusí být
v jednom bloku. Podstatné je, že po prvních dvou odstavcích čtenář ví,
o jakou zakázku šlo, o co se vedl spor a proč ho to má zajímat.

Výsledek řízení, tedy zda úřad rozklad zamítl, rozhodnutí zrušil nebo změnil,
zmiň v úvodním odstavci slovy. Bez spisové značky, ta je až dole.

### Závěr příspěvku

Příspěvek vždy končí odkazem na rozhodnutí a podpisem. Podpis se cituje
doslova, nepřepisuj ho:

```
🤖 I s tímto rozhodnutím pracuje TENDERIX | První AI ve veřejných zakázkách při vyhledávání v rozhodovací praxi ÚOHS, judikatuře a právních předpisech pro veřejné zakázky.
```

Za podpisem následují už jen hashtagy.

### Emoji

Používej je s rozvahou a citem. Drž se ustálené kostry, tedy 🟣 na začátku,
📌 u závěrů, 🏛️ u označení rozhodnutí dole a 🤖 u podpisu. V prvním komentáři
pak 🔗 u odkazu. Nic dalšího nepřidávej. Žádné emoji uvnitř odstavců, žádné ozdoby u hashtagů, nic
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

Carousel má tři druhy stránek. Obálku, slidy se závěry a závěrečnou
brandovou stránku, která je v šabloně napevno a nic se do ní nepíše.

### Obálka, slide 1

Ve feedu se z celého carouselu ukáže jen tahle jedna stránka. Rozhoduje
o tom, jestli někdo vůbec swipne dál, takže na ni nepatří výklad, ale
jedna velká myšlenka.

```
### Slide 1 — obálka

NADPIS: [4–8 slov, otázka nebo tvrzení k tématu]

*Rozhodnutí [orgán] č. j. [čj.], sp. zn.: [sp.zn.] ze dne [datum]:*
```

Nadpis drž krátký, ať se vejde velkým písmem. Funguje otázka, kterou
si zadavatel sám klade, nebo tvrzení proti běžnému očekávání. Může,
ale nemusí být shodný s hákem v textu příspěvku.

- Slabé: „Náležitosti oznámení o výběru"
- Silné: „Musí zadavatel opsat celé životopisy?"

### Slidy se závěry, slide 2 a dál

Vytáhni 3 až 6 nosných závěrů, každý jako jeden slide:

```
### Slide N

[Klíčový závěr, zobecnitelný pro praxi.
**Nejdůležitější části tučně** a zbytek normálně.]

> 📎 Zdroj: bod [N] odůvodnění
```

Označení rozhodnutí na těchhle slidech **není**. Je na obálce a na závěrečné
brandové stránce, což čtenáři stačí. Na každém slidu jen zabíralo místo.

### Délka slidu

**Jeden závěr je vždy jeden slide.** Nikdy ho nerozděluj na dva. Čtenář často
vidí jen jednu stránku z carouselu a půlka myšlenky mu nedá nic. Soudržnost
závěru je důležitější než počet řádků.

Cíl jsou tři až čtyři řádky, zhruba 200 až 260 znaků. Ber to jako mířidlo,
ne jako strop. Osm řádků drobného textu na mobilu nikdo nečte, ale závěr,
který potřebuje pět řádků, si těch pět řádků vezme.

Zkracuj tedy formulaci, ne obsah. Vypustit jde opis skutkového stavu, jména
institutů, která si čtenář domyslí, vysvětlující vsuvky v závorkách a rozvité
přívlastky. Vypustit nesmíš podmínku, za které závěr platí, a rozsah, na který
dopadá. Právě ty dvě věci dělají ze závěru použitelné pravidlo, bez nich
zbude jen dobře znějící slogan.

Když je po zkrácení slide pořád dlouhý, je to většinou signál, že se v něm
schovávají dva různé závěry. Pak je od sebe odděl a udělej z nich dva slidy,
každý s vlastní pointou. To je něco jiného než trhat jeden závěr na půl.

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

## Step 9 — Zpětná kontrola tvrzení

Povinný krok. Draft je v tuhle chvíli hotový, ale nepředkládej ho, dokud
neprojde kontrolou. Píšeš z paměti na to, co jsi četl před mnoha kroky,
a právě tam vznikají posuny a domyšlené detaily.

**Postup.** Vrať se k textu rozhodnutí ve `$scratch`. Když ho už nemáš
v kontextu, načti ho znovu nástrojem Read, ať kontroluješ proti zdroji
a ne proti vlastní vzpomínce. Pak projdi draft po jednotlivých tvrzeních,
tedy věty úvodu, každý analytický odstavec, každý 📌 závěr a každý slide.

U každého tvrzení si odpověz na tři otázky:

1. **Je to v rozhodnutí?** Najdi konkrétní bod odůvodnění, který to říká.
   Když ho nenajdeš, tvrzení škrtni. Nehledej ho „nějak jinde", škrtni.
2. **Říká to takhle silně?** Porovnej modalitu. Rozhodnutí často říká
   „za těchto okolností", „v posuzovaném případě", „nelze vyloučit".
   Když to v draftu vyznívá jako obecné pravidlo, oprav formulaci.
3. **Mluví tam úřad?** Ověř, že pasáž je z hodnotící části a ne z reprodukce
   tvrzení účastníka. Viz Step 8.

**Zvlášť si ověř tyhle věci, protože se v nich chybuje nejčastěji:**

- **Čísla.** Každé procento, částka, lhůta, počet dnů a výše pokuty.
  Porovnej znak po znaku s textem, ne od oka.
- **Paragrafy.** Každý odkaz na ZZVZ včetně odstavce a písmene. Záměna
  § 222 odst. 4 písm. b) za odst. 6 mění smysl celého závěru.
- **Hlavička.** Č. j., sp. zn. a datum proti PDF a detailní stránce.
- **Výsledek řízení.** Potvrdil, zrušil, změnil, zamítl, zastavil.
  U rozkladu i to, zda uspěl celý nebo jen zčásti.
- **Kdo je kdo.** Zadavatel, navrhovatel, vybraný dodavatel a obviněný
  se v textu snadno prohodí, zvlášť když příspěvek anonymizuješ.
- **Čísla bodů u slidů.** Otevři ten bod a přečti si ho. Číslo, které jsi
  odhadl podle pořadí, je skoro jistě špatně.

**Když kontrola něco najde**, oprav to a u dotčeného tvrzení projdi tři
otázky znovu. Oprava jednoho čísla často znamená, že navazující věta
už neplatí.

**Do konverzace pak napiš jeden řádek o tom, jak kontrola dopadla.** Buď že
všechna tvrzení mají oporu v uvedených bodech, nebo co jsi opravil a proč.
Uživatel podle toho pozná, že kontrola opravdu proběhla, a ví, kam se
podívat. Nepiš, že proběhla, když neproběhla.

## Step 10 — Výstup do konverzace

Vypiš výsledek v tomhle členění:

---
📝 **TEXT LINKEDIN PŘÍSPĚVKU**
*(připraveno ke zkopírování, bez odkazu)*

[celý příspěvek]

*Délka: N znaků*

---
💬 **TEXT PRVNÍHO KOMENTÁŘE**
*(vložte hned po publikaci příspěvku)*

🔗 Rozhodnutí [orgán]: [plná URL detailní stránky]

---
🖼️ **TEXTY PRO CANVA SLIDES**
*(zkopírujte každý slide do šablony, tučné části zvýrazněte)*

[obálka a slidy]

---

## Step 11 — Vyrob carousel v Canvě

Šablona je design **`DAHUogc13KY`**. Nikdy do ní nezasahuj, vždy pracuj s kopií.

Struktura šablony:

| Stránka | Role |
|---|---|
| 1 | Obálka. Velký nadpis, krémová bublina s označením rozhodnutí, silueta budovy |
| 2–5 | Slidy se závěry. Jedno textové pole s citací, bez označení rozhodnutí |
| 6–7 | Závěrečné brandové stránky, nic se do nich nepíše |

### Postup

**1. Zkopíruj jen potřebné stránky.** Když máš N závěrů, vezmi obálku, N slidů
a obě závěrečné:

```
copy-design(design_id: "DAHUogc13KY", page_numbers: [1, 2, ..., N+1, 6, 7])
```

Šablona má čtyři stránky na závěry, takže N je nejvýš 4. Když jich máš víc,
buď vyber ty nejsilnější, nebo řekni uživateli, ať si v šabloně stránky
zduplikuje.

**2. Otevři kopii k editaci.** `read-design` s `open_transaction: true`.
Vrátí `transaction_id` a u každého prvku `locator_id`.

**3. Obálka.** `replace_text` na velké textové pole s nadpisem a na text
v bublině. Do bubliny patří krátké označení ve tvaru
`ÚOHS-{čj} ze dne {datum}`, delší se do bubliny nevejde a zalomí se.

**4. Slidy se závěry.** Tohle je jediné místo, kde se to dělá jinak, než
by člověk čekal, a stojí za to pochopit proč.

Text citace je v šabloně uložený jako **posloupnost úseků**, kde se střídají
krémové běžné a mátové tučné. Kdybys použil `replace_text`, sloučí se to
do jednoho úseku a **zvýraznění zmizí**. Proto se nahrazuje
`find_and_replace_text` **úsek po úseku**, kde `find_text` je stávající text
daného úseku. Formátování tím zůstane zachované.

Prakticky to znamená, že **nový závěr musíš napsat rozdělený na stejný počet
úseků, jaký má daná stránka šablony**, se stejným střídáním. Přečti si tedy
regiony stránky a teprve pak text poskládej. Jsi to ty, kdo ten text píše,
takže se dá napsat rovnou tak, aby vzor seděl.

Když je v šabloně úsek, pro který nemáš obsah, nahraď ho jednou mezerou.
Prázdný řetězec projít nemusí.

**5. Ulož.** `edit-design` s `finalize: "commit"` a prázdnými operacemi.

**6. Vypiš uživateli `edit_url` kopie.**

### Na co si dát pozor

- **Formátování občas přeteče.** Když se nahrazuje běžný úsek sousedící
  s tučným, může si vzít tučný řez. Je to jedno kliknutí na opravu, ale
  uživatele na to upozorni, ať to nepřehlédne.
- **Delší text přeteče stránku.** Písmo je 54 bodů a pole má 960 bodů šířky,
  takže se na stránku vejde zhruba 260 znaků pohodlně a 400 na hraně. Drž se
  délky ze Step 8 a je to bez problému.
- **Tučné zvýraznění v Canvě odpovídá `**tučně**` z výstupu ve Step 10.**
  Rozdělení na úseky musí sedět na to, co jsi vypsal do konverzace, ať se
  uživateli obojí shoduje.

### Když Canva selže

Konektor nemusí být připojený nebo může chybět oprávnění. V tom případě
napiš uživateli, že carousel se nepodařilo vyrobit, a připomeň, že texty
slidů má vypsané ve Step 10 a může je vložit do šablony ručně. Zbytek
běhu tím není dotčený.

## Step 12 — Založ Issue

Obsah je stejný jako ve Step 10. Text **nevkládej přímo do příkazu**, ani
do PowerShell heredocu. Uvozovky, `$` a zpětná lomítka v textu by se rozbily.

Napiš tělo Issue nástrojem Write do `$scratch\issue_body.md` a pak:

```powershell
$title = "Tip z praxe — $(Get-Date -Format 'dd.MM.yyyy') — [předmět, max 60 znaků]"
gh issue create --repo Agillis24/uohs_marketing --title $title --label "tip-z-praxe" --body-file "$scratch\issue_body.md"
```

Tělo Issue obsahuje tabulku s metadaty rozhodnutí, celý text příspěvku
v bloku kódu, text prvního komentáře, obálku a všechny slidy, odkaz
na detail na webu ÚOHS a odkaz na vyrobený carousel v Canvě ze Step 11.

Po založení vypiš uživateli URL Issue.

## Step 13 — Zapiš zpracované rozhodnutí

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
  a u slidů uveď, že čísla bodů nejsou k dispozici. Zpětná kontrola pak
  probíhá jen proti shrnutí, což je slabší opora. Napiš to uživateli
  a drž tvrzení opatrněji, ať nestavíš na něčem, co nemáš ověřené.
- **zpětná kontrola najde tvrzení bez opory** — škrtni ho a text přepiš.
  Když po škrtání zbude málo obsahu, radši sáhni po jiném rozhodnutí,
  než abys příspěvek dopisoval domněnkami
- **web ÚOHS nedostupný** — řekni to a skonči
- **žádná nová rozhodnutí** — řekni to a skonči
- **PDF se nepodaří stáhnout u všech kandidátů** — zkus WebFetch shrnutí,
  a když ani to ne, skonči
- **Canva selže nebo není připojená** — řekni to, připomeň, že texty slidů
  jsou vypsané ve Step 10 a jdou vložit ručně, a pokračuj dál
- **založení Issue selže** — výstup stejně ukaž, vypiš chybu a pokračuj
