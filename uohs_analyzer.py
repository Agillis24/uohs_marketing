#!/usr/bin/env python3
"""
ÚOHS Decision Analyzer
Každý týden automaticky projde nová rozhodnutí ÚOHS, vybere nejzajímavější
a připraví návrh LinkedIn příspěvku (text + texty pro Canva slides)
jako GitHub Issue.
"""

import os
import json
import re
import time
import io
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pdfplumber
from openai import OpenAI

# ── Konfigurace ───────────────────────────────────────────────────────────────

UOHS_LIST_URL = "https://uohs.gov.cz/cs/verejne-zakazky/sbirky-rozhodnuti.html?new=1"
UOHS_BASE_URL = "https://uohs.gov.cz"
PROCESSED_FILE = "processed_decisions.json"
MAX_DECISIONS_TO_ANALYZE = 15  # max nových rozhodnutí za jeden běh

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; UOHS-Analyzer/1.0; +https://tenderix.cz)"
}

# ── Správa stavu (která rozhodnutí už byla zpracována) ────────────────────────

def load_processed() -> set:
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_processed(processed: set):
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(processed), f, ensure_ascii=False, indent=2)


# ── Scraping ÚOHS ─────────────────────────────────────────────────────────────

def get_decision_detail_urls() -> list[dict]:
    """Ze stránky se seznamem rozhodnutí vytáhne všechny URL detailů."""
    resp = requests.get(UOHS_LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    decisions = []
    seen_ids = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = re.search(r"/sbirky-rozhodnuti/detail-(\d+)\.html", href)
        if m:
            detail_id = m.group(1)
            if detail_id not in seen_ids:
                seen_ids.add(detail_id)
                full_url = (UOHS_BASE_URL + href) if href.startswith("/") else href
                decisions.append({
                    "id": detail_id,
                    "url": full_url,
                    "link_text": a.get_text(strip=True),
                })

    return decisions


def get_pdf_url_and_metadata(detail_url: str) -> dict:
    """Z detailní stránky rozhodnutí vytáhne URL PDF a metadata."""
    resp = requests.get(detail_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # PDF odkaz — hledáme href končící .pdf nebo obsahující /download/
    pdf_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") or "/download/" in href.lower():
            pdf_url = (UOHS_BASE_URL + href) if href.startswith("/") else href
            break

    # Č.j.
    cj_match = re.search(
        r"číslo\s+jednací[:\s]+(\S+(?:\s+\S+){0,2})",
        page_text, re.IGNORECASE
    )
    cj = cj_match.group(1).strip() if cj_match else ""

    # Sp.zn.
    spzn_match = re.search(
        r"spisov[aá]\s+zna[cč]ka[:\s]+([A-Z]\d+/\d+/[A-Z]+)",
        page_text, re.IGNORECASE
    )
    spzn = spzn_match.group(1).strip() if spzn_match else ""

    # Datum nabytí právní moci
    date_match = re.search(
        r"nabyt[ií]\s+pr\.?\s*moci[:\s]+(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})",
        page_text, re.IGNORECASE
    )
    date = date_match.group(1).strip() if date_match else ""

    # Instance
    instance = "II." if "II. instance" in page_text else "I."

    # Nadpis / předmět
    h1 = soup.find("h1")
    subject = h1.get_text(strip=True) if h1 else ""

    return {
        "pdf_url": pdf_url,
        "cj": cj,
        "spzn": spzn,
        "date": date,
        "instance": instance,
        "subject": subject,
        "detail_url": detail_url,
    }


def download_and_extract_pdf(pdf_url: str) -> str:
    """Stáhne PDF a extrahuje text pomocí pdfplumber."""
    resp = requests.get(pdf_url, headers=HEADERS, timeout=120)
    resp.raise_for_status()

    parts = []
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)

    full_text = "\n".join(parts)
    # Omezíme na ~60 000 znaků (~15 000 tokenů) kvůli limitům API
    return full_text[:60000]


# ── AI analýza (GitHub Models — GPT-4o, zdarma) ──────────────────────────────

SYSTEM_PROMPT = """Jsi expert na česká práva veřejných zakázek. Pracuješ pro platformu TENDERIX
a připravuješ obsah pro LinkedIn příspěvky "Tip z praxe" na základě rozhodnutí ÚOHS.

Tvůj úkol:
1. Posoudit, jak zajímavé a zobecnitelné je rozhodnutí pro aplikační praxi
   zadavatelů a dodavatelů (skóre 1–10).
2. Extrahovat 3–6 klíčových závěrů vhodných pro LinkedIn carousel slides
   (každý slide = jeden závěr, 2–5 vět).
3. Napsat celý LinkedIn příspěvek přesně podle níže uvedené šablony.

── ŠABLONA LINKEDIN PŘÍSPĚVKU ──────────────────────────────────────────────────
🟣 Tip z praxe: [výstižný titulek tématu]

🏛️ [Orgán — "Předseda ÚOHS" nebo "ÚOHS"] v rozhodnutí č. j. [čj.], sp. zn. [sp.zn.],
ze dne [datum] [stručný výsledek: potvrdil/zamítl/zrušil + o čem, 1–2 věty]

[Odstavec: jádro sporu — co bylo předmětem přezkumu, 3–5 vět]

[2–4 odstavce: rozbor klíčových závěrů s konkrétními praktickými dopady]

Z tohoto rozhodnutí podle nás plynou pro zadavatelskou praxi zejména:
📌 [závěr 1]
📌 [závěr 2]
📌 [závěr 3]
📌 [závěr 4, pokud relevantní]

🔗 Rozhodnutí předsedy ÚOHS: [URL detailu]

🤖 I s tímto rozhodnutím pracuje TENDERIX | První AI ve veřejných zakázkách
při vyhledávání v rozhodovací praxi ÚOHS, judikatuře a právních předpisech pro veřejné zakázky.

hashtag#verejnezakazky hashtag#ZZVZ hashtag#UOHS [2–3 tematické hashtagy] hashtag#TENDERIX
────────────────────────────────────────────────────────────────────────────────

── SLIDES ──────────────────────────────────────────────────────────────────────
Každý slide musí mít:
- quote: 2–5 vět, klíčový zobecnitelný závěr. Tučné části vyznač takto: [BOLD]text[/BOLD]
- citation: přesné označení rozhodnutí ve formátu:
  "Rozhodnutí předsedy ÚOHS č. j. XXXX, sp. zn.: YYYY ze dne DD. M. RRRR:"
────────────────────────────────────────────────────────────────────────────────

Odpovídej VŽDY v JSON formátu (bez markdown bloků, čistý JSON):
{
  "interest_score": 8,
  "interest_reason": "Proč je zajímavé pro praxi (1–2 věty)...",
  "slides": [
    {
      "quote": "Text citátu. [BOLD]Klíčová část tučně[/BOLD], zbytek normálně.",
      "citation": "Rozhodnutí předsedy ÚOHS č. j. XXXX, sp. zn.: YYYY ze dne DD. M. RRRR:"
    }
  ],
  "linkedin_post": "Celý text LinkedIn příspěvku přesně dle šablony..."
}"""


def analyze_with_ai(pdf_text: str, metadata: dict) -> dict:
    """Pošle text rozhodnutí do Groq API (Llama 3.3 70B, zdarma) a vrátí analýzu."""
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
    )

    user_prompt = f"""Analyzuj toto rozhodnutí ÚOHS a připrav obsah pro LinkedIn příspěvek TENDERIX:

Číslo jednací: {metadata.get('cj', 'N/A')}
Spisová značka: {metadata.get('spzn', 'N/A')}
Datum nabytí pr. moci: {metadata.get('date', 'N/A')}
Instance: {metadata.get('instance', 'N/A')}
Předmět / název: {metadata.get('subject', 'N/A')}
URL detailu: {metadata.get('detail_url', 'N/A')}

--- TEXT ROZHODNUTÍ (začátek) ---
{pdf_text}
--- KONEC TEXTU ---"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=4000,
    )

    return json.loads(response.choices[0].message.content)


# ── GitHub Issue ──────────────────────────────────────────────────────────────

def create_github_issue(metadata: dict, analysis: dict) -> str:
    """Vytvoří GitHub Issue s návrhem LinkedIn příspěvku."""

    # Naformátuje slides pro markdown — [BOLD]...[/BOLD] → **...**
    slides_md = ""
    for i, slide in enumerate(analysis.get("slides", []), 1):
        quote = re.sub(
            r"\[BOLD\](.*?)\[/BOLD\]", r"**\1**",
            slide.get("quote", ""), flags=re.DOTALL
        )
        citation = slide.get("citation", "")
        slides_md += f"### Slide {i}\n\n> {quote}\n>\n> _{citation}_\n\n---\n\n"

    issue_body = f"""## 🟣 Návrh příspěvku — Tip z praxe

| Pole | Hodnota |
|------|---------|
| **Předmět** | {metadata.get('subject', '—')} |
| **Č.j.** | {metadata.get('cj', '—')} |
| **Sp.zn.** | {metadata.get('spzn', '—')} |
| **Datum** | {metadata.get('date', '—')} |
| **Instance** | {metadata.get('instance', '—')} |
| **Zajímavost pro praxi** | {analysis.get('interest_score', '—')}/10 |
| **Detail ÚOHS** | [{metadata['detail_url']}]({metadata['detail_url']}) |

> **Proč zajímavé:** {analysis.get('interest_reason', '—')}

---

## 📝 TEXT LINKEDIN PŘÍSPĚVKU

_Zkontrolujte, upravte a zkopírujte na LinkedIn:_

```
{analysis.get('linkedin_post', '(text nebyl vygenerován)')}
```

---

## 🖼️ TEXTY PRO CANVA SLIDES

_Zkopírujte každý slide do šablony v Canvě. Části označené **tučně** zvýrazněte i v Canvě._

{slides_md}
## ✅ Postup publikace

1. [ ] Zkontrolujte a upravte text LinkedIn příspěvku výše
2. [ ] Zkopírujte texty slidů do Canva šablony (tučné části zvýrazněte)
3. [ ] Exportujte slides z Canvy
4. [ ] Publikujte na LinkedIn

---
_Vygenerováno automaticky: {datetime.utcnow().strftime('%d. %m. %Y %H:%M')} UTC_"""

    title = (
        f"Tip z praxe — {datetime.utcnow().strftime('%d. %m. %Y')} — "
        f"{metadata.get('subject', 'nové rozhodnutí')[:70]}"
    )

    owner, repo = GITHUB_REPOSITORY.split("/", 1)
    resp = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={
            "title": title,
            "body": issue_body,
            "labels": ["tip-z-praxe"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


# ── Hlavní logika ─────────────────────────────────────────────────────────────

def main():
    sep = "=" * 60
    print(sep)
    print(f"ÚOHS Analyzer — {datetime.utcnow().strftime('%d. %m. %Y %H:%M')} UTC")
    print(sep)

    processed = load_processed()
    print(f"Již zpracovaných rozhodnutí: {len(processed)}")

    print("\n📋 Stahuji seznam nových rozhodnutí z ÚOHS...")
    all_decisions = get_decision_detail_urls()
    new_decisions = [d for d in all_decisions if d["id"] not in processed]
    print(f"Na webu celkem: {len(all_decisions)} | Nových (nezpracovaných): {len(new_decisions)}")

    if not new_decisions:
        print("\n✅ Žádná nová rozhodnutí tento týden. Končím.")
        return

    # Analyzujeme maximálně MAX_DECISIONS_TO_ANALYZE nových rozhodnutí
    to_analyze = new_decisions[:MAX_DECISIONS_TO_ANALYZE]
    best_score = -1
    best_result = None  # (metadata, analysis)

    for i, decision in enumerate(to_analyze, 1):
        print(f"\n[{i}/{len(to_analyze)}] 🔍 {decision['url']}")
        time.sleep(1)  # zdvořilé crawlování

        try:
            metadata = get_pdf_url_and_metadata(decision["url"])

            if not metadata["pdf_url"]:
                print("   ⚠️  PDF nenalezeno, přeskakuji.")
                processed.add(decision["id"])
                continue

            print(f"   📄 PDF: {metadata['pdf_url']}")
            pdf_text = download_and_extract_pdf(metadata["pdf_url"])

            if len(pdf_text) < 500:
                print("   ⚠️  Příliš krátký text, přeskakuji.")
                processed.add(decision["id"])
                continue

            print(f"   🤖 Analyzuji ({len(pdf_text):,} znaků)...")
            analysis = analyze_with_ai(pdf_text, metadata)
            score = int(analysis.get("interest_score", 0))
            reason = analysis.get("interest_reason", "")[:100]
            print(f"   ⭐ Skóre: {score}/10 — {reason}")

            if score > best_score:
                best_score = score
                best_result = (metadata, analysis)

            processed.add(decision["id"])
            time.sleep(2)  # respektujeme rate limity API

        except Exception as exc:
            print(f"   ❌ Chyba: {exc}")
            continue

    # Uložíme stav
    save_processed(processed)
    print(f"\n💾 Stav uložen ({len(processed)} zpracovaných rozhodnutí).")

    if best_result is None:
        print("\n❌ Nepodařilo se zpracovat žádné rozhodnutí. Zkontrolujte logy.")
        return

    metadata, analysis = best_result
    print(f"\n🏆 Nejzajímavější rozhodnutí (skóre {best_score}/10):")
    print(f"   Předmět: {metadata.get('subject', 'N/A')}")
    print(f"   Sp.zn.:  {metadata.get('spzn', 'N/A')}")
    print(f"   Slides:  {len(analysis.get('slides', []))}")

    print("\n📬 Vytvářím GitHub Issue s návrhem příspěvku...")
    issue_url = create_github_issue(metadata, analysis)
    print(f"✅ Issue vytvořeno: {issue_url}")
    print("\nDostanete e-mail s notifikací. Otevřete Issue, zkontrolujte a publikujte.")


if __name__ == "__main__":
    main()
