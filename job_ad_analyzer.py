import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # a .env fájlt automatikusan betölti a process környezetébe, terminál-beállítástól függetlenül
except ImportError:
    pass  # ha nincs telepítve a python-dotenv, a script még mindig működik, ha a változó máshogy van beállítva

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
6. NE találj ki tapasztalatot vagy skill-szintet, ami nincs a profilban. Ha valami nincs benne, azt hiányzó készségként kezeld.

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


def call_claude(prompt: str) -> dict:
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
        max_tokens=1000,
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
    args = parser.parse_args()

    profile = load_profile(Path(args.profile))
    job_ad_text = read_job_ad(args)
    prompt = build_prompt(profile, job_ad_text)

    if args.dry_run:
        print(prompt)
        return

    result = call_claude(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()