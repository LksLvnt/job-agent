import json
import sys
from pathlib import Path

import job_ad_analyzer as jaa
import cv_customizer as cvc

PROFILE_PATH = jaa.DEFAULT_PROFILE_PATH


def read_multiline(prompt: str) -> str:
    print(prompt)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break

        stripped = line.strip()

        if not lines and stripped.lower() == "quit":
            return "quit"

        if not lines and stripped and Path(stripped).exists() and Path(stripped).is_file():
            print(f"(Fájlból olvasva: {stripped})")
            return Path(stripped).read_text(encoding="utf-8")

        if stripped == "END":
            break
        lines.append(line)

    return "\n".join(lines).strip()


def ask_yes_no(prompt: str) -> bool:
    answer = input(f"{prompt} (i/n): ").strip().lower()
    return answer in ("i", "igen", "y", "yes")


def main():
    if not PROFILE_PATH.exists():
        print(f"HIBA: nem található a self-profil itt: {PROFILE_PATH}", file=sys.stderr)
        sys.exit(1)

    profile = jaa.load_profile(PROFILE_PATH)
    print("=== job-agent interaktív mód ===")
    print("Minden körben: illessz be egy hirdetést és zárd END sorral,")
    print("VAGY írd be egy .txt fájl elérési útját egyetlen sorban (nincs szükség END-re),")
    print("VAGY írd be: quit a kilépéshez (bármikor, azonnal hat).\n")

    while True:
        job_ad_text = read_multiline("--- Illeszd be a hirdetést (END a végén, vagy 'quit' a kilépéshez) ---")

        if job_ad_text.strip().lower() == "quit":
            print("Kilépés.")
            break
        if not job_ad_text.strip():
            print("Üres bemenet, próbáld újra.\n")
            continue

        print("\nElemzés fut...\n")
        analysis_prompt = jaa.build_prompt(profile, job_ad_text)
        analysis = jaa.call_claude_json(analysis_prompt)
        print("=== RELEVANCIA-ELEMZÉS ===")
        print(json.dumps(analysis, ensure_ascii=False, indent=2))

        if analysis.get("scam_risk", {}).get("level") in ("medium", "high"):
            print("\n⚠️  FIGYELEM: a hirdetés gyanús elemeket tartalmazhat - nézd át a scam_risk mezőt "
                  "alaposan, mielőtt jelentkeznél.")

        if ask_yes_no("\nGenerálj motivációs levelet ehhez?"):
            letter_prompt = jaa.build_letter_prompt(profile, job_ad_text, analysis)
            letter = jaa.call_claude_raw(letter_prompt)
            print("\n=== MOTIVÁCIÓS LEVÉL ===")
            print(letter)

        if ask_yes_no("\nGenerálj testreszabott CV-t ehhez?"):
            company = input("Cégnév (opcionális, Enter a kihagyáshoz): ").strip() or None
            approved_projects = cvc.get_approved_projects(profile, allow_unapproved=False)
            cv_prompt = cvc.build_prompt(profile, job_ad_text, approved_projects)
            decision = cvc.call_claude_json(cv_prompt)

            template = cvc.TEMPLATE_PATH.read_text(encoding="utf-8")
            summary_text = ("Software developer working across Angular, React, and backend frameworks "
                             "in Python and Java. Builds full-stack projects end to end, from database "
                             "design to CI/CD deployment.")
            filled = template.replace("{{SUMMARY}}", summary_text)
            filled = filled.replace("{{SKILLS_GRID}}", cvc.render_skills_grid(decision["technical_skills"]))
            filled = filled.replace("{{PROJECTS}}", cvc.render_projects(decision["project_order"], approved_projects))
            include_languages = bool(profile.get("nyelvtudas"))
            filled = filled.replace("{{LANGUAGES_SECTION}}", cvc.render_languages_section(profile, include_languages))

            class Args:
                pass
            fake_args = Args()
            fake_args.output = None
            fake_args.company = company
            fake_args.job_ad = None
            output_path = cvc.build_output_path(fake_args)
            output_path.write_text(filled, encoding="utf-8")
            print(f"\nCV elmentve ide: {output_path}")

        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()