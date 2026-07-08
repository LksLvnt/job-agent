import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_PROFILE_PATH = Path(__file__).parent / "self_profile.json"


def load_profile(path: Path) -> dict:
    if not path.exists():
        print(f"HIBA: nem található a self-profil itt: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_job_ad(args) -> str:
    if args.job_ad:
        job_ad_path = Path(args.job_ad)
        if not job_ad_path.exists():
            print(f"HIBA: nem található a fájl: {job_ad_path}", file=sys.stderr)
            sys.exit(1)
        return job_ad_path.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("HIBA: adj meg egy --job-ad fájlt, vagy pipe-old be stdin-en.", file=sys.stderr)
    sys.exit(1)


def build_prompt(profile: dict, job_ad_text: str) -> str:
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)

    return f"""Az alábbiakban egy jelölt strukturált készség-profilja (JSON), majd egy állashirdetés szövege található.

Feladatod:
1. Értékeld a hirdetés és a profil illeszkedését.
2. Sorold fel, mely elvárt készségek egyeznek meg a jelölt meglévő tudásával (skill szint feltüntetésével).
3. Sorold fel, mely elvárt készségek hiányoznak vagy gyengék a jelölt profiljában.
4. Adj egy 1-10 közötti relevancia-pontszámot, ahol 10 = tökéletes illeszkedés, 1 = egyáltalán nem illik.
5. Jelezd, ha vannak "stretch" elemek - olyan elvárások, amik nem felelnek meg tökéletesen, de a jelölt meglévő tapasztalata alapján ésszerű időn belül pótolhatók.
6. NE találj ki tapasztalatot vagy skill-szintet, ami nincs a profilban. Ha valami nincs benne, azt hiányzó készségként kezeld. Ez akkor is érvényes, ha a hiányzó készség "valószínűnek" tűnik egy kapcsolódó technológia ismeretéből (pl. NE írd, hogy "valószínűleg ismeri az RxJS-t, mert Angular fejlesztő" - ha nincs explicit a profilban, az gap_skills, nem stretch_feasible feltételezés).

Válaszolj KIZÁRÓLAG az alábbi JSON formátumban, semmi mást ne írj a válaszba:

{{
  "relevance_score": <1-10 egész szám>,
  "matching_skills": ["skill neve (szint)", ...],
  "gap_skills": ["skill neve", ...],
  "stretch_feasible": ["skill neve - miért pótolható ésszerű időn belül", ...],
  "reasoning": "2-3 mondatos indoklás a pontszámra"
}}

--- JELÖLT PROFIL ---
{profile_json}

--- ÁLLÁSHIRDETÉS ---
{job_ad_text}
"""


def build_letter_prompt(profile: dict, job_ad_text: str, analysis: dict) -> str:
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)

    return f"""Írj egy magyar nyelvű, testreszabott motivációs levelet az alábbi jelölt profilja
és az állashirdetés alapján. Az elemzés eredménye (matching_skills, stretch_feasible) segít
eldönteni, mire fókuszálj.

Szigorú szabályok:
1. KIZÁRÓLAG a jelölt profiljában (kiemelt_projektek, nyelvek_es_keretrendszerek, stb.) szereplő
   tényleges projekteket, technológiákat és tapasztalatokat említsd. NE találj ki semmit, ami nincs
   a profilban - se projektnevet, se konkrét eredményt, se évszámot.
2. Ha a "figyelmeztetes" mező szerepel egy projektnél (pl. félkész README), NE hivatkozz rá úgy,
   mintha az a projekt teljesen kész és lezárt lenne - fogalmazz óvatosan, vagy kerüld az adott
   projekt túlzott kiemelését.
3. Legyen konkrét, ne általános - emelj ki 1-2 releváns projektet a matching_skills alapján,
   ne sorold fel az összes skillt.
4. Hossz: kb. 200-300 szó, formális, de nem túlzottan merev hangnem.
5. NE használj klisé-nyitómondatot ("Nagy érdeklődéssel olvastam..." típusú frázisokat kerüld).
6. A levél végén NE generálj kitalált elérhetőséget vagy dátumot - ezeket a jelölt maga tölti ki.
7. KRITIKUS: a "gap_skills" listában szereplő készségekről SOSE állítsd, hogy a jelölt ismeri,
   érti, vagy "tisztában van" velük - még burkoltan, finomítva sem ("valószínűleg ismeri",
   "biztosan találkozott vele", "tisztában van az alapjaival"). Ha egy gap_skill releváns a
   hirdetéshez, VAGY hagyd ki teljesen a levélből, VAGY legfeljebb egy őszinte tanulási
   szándékot fogalmazz meg ("szívesen elmélyülnék X-ben"), de SOHA ne állíts meglévő tudást.
8. NE használj szó szerinti szint-címkéket a szövegben (pl. "intermediate szinten",
   "advanced szinten", "beginner szinten") - ezek belső kategóriák, nem természetes
   megfogalmazások egy valódi motivációs levélben. Írd le természetes nyelven, mit csináltál
   az adott technológiával, ne kategorizáld számszerűen/címkével.

Válaszolj KIZÁRÓLAG a motivációs levél szövegével, semmi mást ne írj (se magyarázatot, se JSON-t,
se Markdown-fence-t).

--- JELÖLT PROFIL ---
{profile_json}

--- ELŐZETES ELEMZÉS ---
{analysis_json}

--- ÁLLÁSHIRDETÉS ---
{job_ad_text}
"""


def call_claude_raw(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("HIBA: hiányzik az 'anthropic' csomag. Telepítsd: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("HIBA: nincs beállítva az ANTHROPIC_API_KEY környezeti változó.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text


def call_claude_json(prompt: str) -> dict:
    text = call_claude_raw(prompt)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("FIGYELEM: a válasz nem volt tiszta JSON, nyers szöveg:", file=sys.stderr)
        print(text, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Állashirdetés relevancia-elemzése a self-profil alapján.")
    parser.add_argument("--job-ad", help="Útvonal a hirdetés szövegét tartalmazó fájlhoz.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE_PATH), help="Útvonal a self_profile.json-hoz.")
    parser.add_argument("--dry-run", action="store_true", help="Csak a promptot írja ki, nem hív API-t.")
    parser.add_argument("--generate-letter", action="store_true",
                         help="Az elemzés után motivációs levelet is generál.")
    args = parser.parse_args()

    profile = load_profile(Path(args.profile))
    job_ad_text = read_job_ad(args)
    analysis_prompt = build_prompt(profile, job_ad_text)

    if args.dry_run:
        print("=== ELEMZÉS PROMPT ===")
        print(analysis_prompt)
        if args.generate_letter:
            print("\n=== MOTIVÁCIÓS LEVÉL PROMPT (elemzés eredménye nélkül, dry-run módban placeholder-rel) ===")
            placeholder_analysis = {"relevance_score": "N/A - dry-run", "matching_skills": [], "gap_skills": [], "stretch_feasible": [], "reasoning": "N/A - dry-run"}
            print(build_letter_prompt(profile, job_ad_text, placeholder_analysis))
        return

    analysis = call_claude_json(analysis_prompt)
    print("=== RELEVANCIA-ELEMZÉS ===")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))

    if args.generate_letter:
        letter_prompt = build_letter_prompt(profile, job_ad_text, analysis)
        letter = call_claude_raw(letter_prompt)
        print("\n=== MOTIVÁCIÓS LEVÉL ===")
        print(letter)


if __name__ == "__main__":
    main()