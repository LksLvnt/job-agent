# job-agent

Személyes álláskereső-segéd. A cél: állashirdetések relevancia-elemzése egy
strukturált self-profil alapján, hogy gyorsabban el lehessen dönteni, mely
hirdetésekre érdemes jelentkezni.

## Jelenlegi állapot (v0.3 - hirdetés-elemzés + motivációs levél + CV-testreszabás)

**Ez a verzió három komponenst tartalmaz**: hirdetés-elemzés, motivációs levél generálás,
és CV-testreszabás egy meglévő HTML-sablon alapján. Nincs benne automatikus
jelentkezés-kitöltés - ez tervezett, de még meg nem épített komponens.

### Mit csinál most

1. **job_ad_analyzer.py**: beolvassa a `self_profile.json`-t és egy hirdetést, a Claude
   API-val relevancia-pontszámot, egyező/hiányzó készségeket ad vissza.
2. **`--generate-letter` flag**: az elemzés eredményét felhasználva motivációs levelet
   generál, KIZÁRÓLAG a self_profile.json-ban szereplő tényleges projektekre hivatkozva.
3. **cv_customizer.py**: a meglévő CV HTML-sablonját tölti ki hirdetés-specifikusan -
   Technical Skills sorrendet igazít, a JÓVÁHAGYOTT projektek közül választ és rendez,
   Languages szekciót ad hozzá (ha van nyelvtudás-adat a profilban). A Summary, Experience,
   Education szekciók VÁLTOZATLANOK maradnak - ezeket a script nem érinti.

### Fontos: minden AI-generált kimenetet át kell nézni küldés előtt

Korábbi futtatásoknál előfordult, hogy a modell (a promptban explicit tiltás ellenére)
meglévő adatot tévesen hiányzónak állított, vagy hiányzó készségről óvatlanul
feltételezést tett. A kritikus döntéseket (pl. Languages szekció megjelenítése) emiatt
kódban kikényszerítjük, nem bízzuk a modellre - de ez nem garancia mindenre. **Minden
motivációs levelet és CV-t el kell olvasni jelentkezés előtt.**

## Telepítés

```bash
pip install -r requirements.txt
cp .env.example .env
# szerkeszd a .env fájlt, add meg a saját ANTHROPIC_API_KEY-edet

cp self_profile.example.json self_profile.json
# töltsd ki a saját, valós készség-profiloddal - ez a fájl NEM kerül git-be
# (bérelvárás és önértékelés érzékeny adat, lásd "Miért nincs a self_profile.json a repóban" lent)
```

## Használat

### Hirdetés-elemzés

```bash
python job_ad_analyzer.py --job-ad hirdetes.txt
python job_ad_analyzer.py --job-ad hirdetes.txt --generate-letter
```

Vagy stdin-ről:

```bash
cat hirdetes.txt | python job_ad_analyzer.py
```

Dry-run (API kulcs nélkül is működik, csak a promptot írja ki, nem hív API-t):

```bash
python job_ad_analyzer.py --job-ad hirdetes.txt --dry-run
```

### CV testreszabás

```bash
python cv_customizer.py --job-ad hirdetes.txt --company "Acme Kft"
```

A generált CV a `generated_cvs/` mappába kerül, egyedi, időbélyeggel ellátott
fájlnévvel (pl. `cv_acme_kft_20260708_1530.html`), hogy sose írja felül a korábbi
verziókat. Ez a mappa NEM kerül git-be (generált kimenet, nem forráskód).

A `--company` opcionális - ha nincs megadva, a hirdetés fájlnevéből generálódik
a kimeneti fájlnév.

## self_profile.json

Ez tartalmazza a strukturált készség-profilt, szint szerint (beginner /
intermediate / advanced), a bérelvárást, és a kiemelt projekteket. Ezt
időnként frissíteni kell, ahogy a tudás és a projektek változnak.

## Tervezett, de még nem épített komponensek

Sorrend szerint:

1. ~~Hirdetés-elemzés~~ (kész, v0.1)
2. ~~Motivációs levél generálás~~ (kész, v0.2)
3. ~~CV testreszabás~~ (kész, v0.3)
4. LinkedIn Easy Apply automatikus kitöltés

## Ismert korlátok

- A self_profile.json-ban több skill-szint becslés alapú, nem objektíven mért
- A relevancia-pontszám annyira jó, amennyire a self_profile.json pontos - ha
  a profil elavul, a pontszám is megbízhatatlanná válik
- A végső jelentkezési döntés mindig emberi kézben marad, az agent csak
  információt szolgáltat