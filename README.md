# job-agent

Személyes álláskereső-segéd. A cél: állashirdetések relevancia-elemzése egy
strukturált self-profil alapján, hogy gyorsabban el lehessen dönteni, mely
hirdetésekre érdemes jelentkezni.

## Jelenlegi állapot (v0.1 - csak hirdetés-elemzés)

**Ez a verzió KIZÁRÓLAG a hirdetés-elemzést csinálja.** Nincs benne CV-generálás,
motivációs levél, vagy automatikus jelentkezés-kitöltés - ezek tervezett, de
még meg nem épített, külön komponensek lesznek.

### Mit csinál most

1. Beolvassa a `self_profile.json`-t (strukturált, szint szerinti készség-profil)
2. Beolvas egy állashirdetés-szöveget (fájlból vagy stdin-ről)
3. A Claude API-nak elküldi mindkettőt, és visszakap egy strukturált értékelést:
   - relevancia-pontszám (1-10)
   - egyező készségek
   - hiányzó készségek
   - "stretch" elemek (nem tökéletes, de ésszerű időn belül pótolható hiányok)
   - rövid indoklás

### Mit NEM csinál (szándékosan, egyelőre)

- Nem generál CV-t vagy motivációs levelet
- Nem tölt ki jelentkezési űrlapokat
- Nem dönt helyetted - csak információt ad, a jelentkezési döntés emberi kézben marad

## Telepítés

```bash
pip install -r requirements.txt
cp .env.example .env
# szerkeszd a .env fájlt, add meg a saját ANTHROPIC_API_KEY-edet
export $(cat .env | xargs)
```

## Használat

```bash
python job_ad_analyzer.py --job-ad hirdetes.txt
```

Vagy stdin-ről:

```bash
cat hirdetes.txt | python job_ad_analyzer.py
```

Dry-run (API kulcs nélkül is működik, csak a promptot írja ki, nem hív API-t -
hasznos a self_profile.json módosításainak ellenőrzésére):

```bash
python job_ad_analyzer.py --job-ad hirdetes.txt --dry-run
```

## self_profile.json

Ez tartalmazza a strukturált készség-profilt, szint szerint (beginner /
intermediate / advanced), a bérelvárást, és a kiemelt projekteket. Ezt
időnként frissíteni kell, ahogy a tudás és a projektek változnak.

## Tervezett, de még nem épített komponensek

Sorrend szerint, a következő lépésekben:

1. ~~Hirdetés-elemzés~~ (kész, ez a v0.1)
2. Motivációs levél generálás
3. Tanulhatóság-becslés (mely hiányzó skillek pótolhatók ésszerű időn belül)
4. CV testreszabás
5. LinkedIn Easy Apply automatikus kitöltés

## Ismert korlátok

- A self_profile.json-ban több skill-szint becslés alapú, nem objektíven mért
- A relevancia-pontszám annyira jó, amennyire a self_profile.json pontos - ha
  a profil elavul, a pontszám is megbízhatatlanná válik
- A végső jelentkezési döntés mindig emberi kézben marad, az agent csak
  információt szolgáltat
