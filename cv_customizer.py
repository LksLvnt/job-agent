import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_PROFILE_PATH = Path(__file__).parent / "self_profile.json"
TEMPLATE_PATH = Path(__file__).parent / "cv_template" / "base_cv_template.html"
OUTPUT_DIR = Path(__file__).parent / "generated_cvs"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:50]


def build_output_path(args) -> Path:
    if args.output:
        return Path(args.output)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    if args.company:
        base_name = slugify(args.company)
    elif args.job_ad:
        base_name = slugify(Path(args.job_ad).stem)
    else:
        base_name = "cv"

    return OUTPUT_DIR / f"cv_{base_name}_{timestamp}.html"


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


def get_approved_projects(profile: dict, allow_unapproved: bool) -> list:
    projects = profile.get("kiemelt_projektek", [])
    if allow_unapproved:
        return projects
    return [p for p in projects if p.get("szerepel_a_cv_n", False)]


def build_prompt(profile: dict, job_ad_text: str, approved_projects: list) -> str:
    relevant_profile = {
        "nyelvtudas": profile.get("nyelvtudas", []),
        "nyelvek_es_keretrendszerek": profile.get("nyelvek_es_keretrendszerek", []),
        "backend_es_api": profile.get("backend_es_api", []),
        "adatbazisok": profile.get("adatbazisok", []),
        "devops_es_infrastruktura": profile.get("devops_es_infrastruktura", []),
        "ai_es_search": profile.get("ai_es_search", []),
    }
    profile_json = json.dumps(relevant_profile, ensure_ascii=False, indent=2)
    projects_json = json.dumps(approved_projects, ensure_ascii=False, indent=2)

    return f"""Az alábbiakban egy jelölt technikai profilja, JÓVÁHAGYOTT projekt-leírásai (készen,
szó szerint felhasználhatók), és egy állashirdetés szövege található.

Feladatod KIZÁRÓLAG a következő döntéseket meghozni, a meglévő szövegek/adatok
ÁTÍRÁSA NÉLKÜL:

1. Technical Skills: a hirdetéshez legjobban illeszkedő technológiákat emeld ki elöl,
   3 kategóriában (Languages, Frameworks, Data / Infra) - a profilban szereplő
   TÉNYLEGES technológiákból válogass, ne találj ki újat. Minden kategóriában
   maximum 4-5 elem legyen, vesszővel elválasztva, ahogy az eredeti CV-n.
2. Projects: a MEGADOTT, jóváhagyott projektek közül válaszd ki és rendezd sorrendbe
   azokat, amik leginkább relevánsak a hirdetéshez. A "cv_szoveg" mezőt SZÓ SZERINT,
   VÁLTOZTATÁS NÉLKÜL használd - ne írd át, ne rövidítsd, ne bővítsd.
3. Languages: ha a profilban van nyelvtudás, és a hirdetés nyelvtudást is elvár vagy
   említ, jelezd, hogy kerüljön be egy Languages szekció.

Válaszolj KIZÁRÓLAG az alábbi JSON formátumban:

{{
  "technical_skills": {{
    "Languages": "elem1, elem2, elem3",
    "Frameworks": "elem1, elem2, elem3",
    "Data / Infra": "elem1, elem2, elem3"
  }},
  "project_order": ["projekt neve pontosan a bemenetből", "..."],
  "include_languages_section": true vagy false,
  "reasoning": "2-3 mondatos indoklás a döntésekről"
}}

--- JELÖLT TECHNIKAI PROFIL ---
{profile_json}

--- JÓVÁHAGYOTT PROJEKTEK (csak ezek közül választhatsz, sorrendet és kiválasztást döntesz el) ---
{projects_json}

--- ÁLLÁSHIRDETÉS ---
{job_ad_text}
"""


def call_claude_json(prompt: str) -> dict:
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
        max_tokens=1200,
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


def render_skills_grid(skills: dict) -> str:
    rows = []
    for cat, values in skills.items():
        rows.append(f'        <div class="cat">{cat}</div><div>{values}</div>')
    return "\n".join(rows)


def render_projects(project_order: list, approved_projects: list) -> str:
    approved_by_name = {p["nev"]: p for p in approved_projects}
    blocks = []
    for name in project_order:
        if name not in approved_by_name:
            print(f"FIGYELEM: a modell '{name}' projektet javasolta, de ez NEM szerepel a "
                  f"jóváhagyott listában - kihagyva.", file=sys.stderr)
            continue
        p = approved_by_name[name]
        blocks.append(f"""      <div class="project">
        <div class="item-header">
          <span class="item-name">{p["nev"]}</span>
          <span class="item-date"></span>
        </div>
        <div class="item-tech">{p["tech"]}</div>
        <div class="item-desc">{p["cv_szoveg"]}</div>
      </div>""")
    return "\n".join(blocks)


def render_languages_section(profile: dict, include: bool) -> str:
    if not include or not profile.get("nyelvtudas"):
        return ""
    langs = profile["nyelvtudas"]
    lang_str = ", ".join(f'{l["nev"]} ({l["level"]})' for l in langs)
    return f"""<div class="section">
      <div class="section-title">Languages</div>
      <div class="edu-line">{lang_str}</div>
    </div>"""


def main():
    parser = argparse.ArgumentParser(description="CV testreszabása egy hirdetéshez, a meglévő sablon alapján.")
    parser.add_argument("--job-ad", help="Útvonal a hirdetés szövegét tartalmazó fájlhoz.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE_PATH), help="Útvonal a self_profile.json-hoz.")
    parser.add_argument("--company", help="Cégnév a kimeneti fájlnévhez (opcionális, ha nincs, a hirdetés fájlnevét használja).")
    parser.add_argument("--output", help="Explicit kimeneti útvonal. Ha nincs megadva, automatikusan generálódik a generated_cvs/ mappába.")
    parser.add_argument("--dry-run", action="store_true", help="Csak a promptot írja ki, nem hív API-t.")
    parser.add_argument("--allow-unapproved", action="store_true",
                         help="Engedélyezi a szerepel_a_cv_n: false projektek választását is (ÓVATOSAN HASZNÁLD).")
    args = parser.parse_args()

    profile = load_profile(Path(args.profile))
    job_ad_text = read_job_ad(args)
    approved_projects = get_approved_projects(profile, args.allow_unapproved)

    if not approved_projects:
        print("HIBA: nincs egyetlen jóváhagyott projekt sem (szerepel_a_cv_n: true).", file=sys.stderr)
        sys.exit(1)

    if args.allow_unapproved:
        print("FIGYELEM: --allow-unapproved aktív, jóvá nem hagyott projekt-szövegek is bekerülhetnek!", file=sys.stderr)

    prompt = build_prompt(profile, job_ad_text, approved_projects)

    if args.dry_run:
        print(prompt)
        return

    decision = call_claude_json(prompt)
    print("=== CV TESTRESZABÁSI DÖNTÉS ===")
    print(json.dumps(decision, ensure_ascii=False, indent=2))

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    summary_text = ("Software developer working across Angular, React, and backend frameworks "
                     "in Python and Java. Builds full-stack projects end to end, from database "
                     "design to CI/CD deployment.")

    filled = template.replace("{{SUMMARY}}", summary_text)
    filled = filled.replace("{{SKILLS_GRID}}", render_skills_grid(decision["technical_skills"]))
    filled = filled.replace("{{PROJECTS}}", render_projects(decision["project_order"], approved_projects))

    include_languages = bool(profile.get("nyelvtudas"))
    if include_languages != decision.get("include_languages_section", False):
        print(f"FIGYELEM: a modell include_languages_section={decision.get('include_languages_section')} "
              f"döntést hozott, de a profilban {'VAN' if include_languages else 'NINCS'} nyelvtudás-adat - "
              f"a kódban kikényszerített szabály felülírja a modell döntését.", file=sys.stderr)
    filled = filled.replace("{{LANGUAGES_SECTION}}", render_languages_section(profile, include_languages))

    output_path = build_output_path(args)
    output_path.write_text(filled, encoding="utf-8")
    print(f"\nCV elmentve ide: {output_path}")
    print("Nyisd meg böngészőben, és nyomtasd PDF-ként, ahogy eddig is csináltad.")


if __name__ == "__main__":
    main()