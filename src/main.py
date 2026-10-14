import feedparser
import os
import json
import time
import requests
import html
import re
import random
import urllib.parse
from datetime import datetime
from image_finder import pronadji_sliku, reset_rotacije

# =====================================================================
# KONFIGURACIJA
# =====================================================================

OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_URL = "https://ollama.com/api/generate"
OLLAMA_MODEL = "gemma4:31b-cloud"

FREENEWS_HOSTS = ["www.kurir.rs", "www.novosti.rs", "www.alo.rs", "n1info.rs"]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
ARHIVA_FOLDER = os.path.join(OUTPUT_FOLDER, "arhiva")
ARHIVA_INDEX = os.path.join(ARHIVA_FOLDER, "index.json")

MAX_VESTI_U_GLAVNOM = 200
MAX_NOVIH_PO_POKRETANJU = 50
VESTI_PO_IZVORU = 8

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KATEGORIJE = ["Hronika", "Društvo", "Ekonomija", "Sport"]

# Vise pretraga po kategoriji - svaka je odvojeni poziv
PRETRAGE = {
    "Hronika": [
        "hapšenje uhapšen priveden",
        "sud tužilaštvo presuda",
        "saobraćajna nesreća poginuo",
        "požar eksplozija",
        "ubistvo napad",
        "krađa razbojništvo",
        "policija istraga droga",
        "sudjenje optužnica pritvor",
    ],
    "Društvo": [
        "vlada ministarstvo",
        "opština grad skupština",
        "izbori protest",
        "zdravstvo obrazovanje škola",
        "poplava sneg oluja vreme",
        "studenti fakultet",
    ],
    "Ekonomija": [
        "cena dinara evra",
        "inflacija plata penzija",
        "budžet investicija",
        "fabrika kompanija privreda",
        "poljoprivreda turizam sajam",
    ],
    "Sport": [
        "crvena zvezda partizan",
        "reprezentacija utakmica",
        "derbi fudbal košarka",
    ],
}

# Specificne Google News pretrage za Hroniku
GOOGLE_NEWS_QUERIES = [
    ("hronika", "Hronika"),
    ("saobraćajna nesreća", "Hronika"),
    ("požar", "Hronika"),
    ("hapšenje", "Hronika"),
    ("sud presuda", "Hronika"),
    ("ubistvo", "Hronika"),
    ("krađa", "Hronika"),
    ("droga zaplena", "Hronika"),
    ("društvo Srbija", "Društvo"),
    ("ekonomija Srbija", "Ekonomija"),
    ("sport Srbija", "Sport"),
]

ATMOSFERA = {
    "Hronika": ["night", "dusk", "foggy", "dark"],
    "Društvo": ["morning", "dawn", "afternoon", "autumn"],
    "Ekonomija": ["dusk", "industrial", "morning", "sunset"],
    "Sport": ["floodlights", "night", "dramatic", "stadium"],
}

# Reci koje UKAZUJU da vest MORA biti Hronika (za validaciju)
HRONIKA_KLJUCNE = [
    "uhapšen", "uhapsen", "hapšenje", "hapsenje", "priveden", "pritvor",
    "sud", "tužilaštvo", "tuzilastvo", "presuda", "optužnica", "optuznica",
    "nesreća", "nesreca", "saobraćajna", "saobracajna", "poginuo", "povređen", "povredjen",
    "požar", "pozar", "eksplozija", "ubistvo", "ubica", "napad", "krađa", "kradja",
    "razbojništvo", "razbojnistvo", "policija", "mup", "istraga", "droga",
    "narkotik", "zaplena", "kriminal", "zločin", "zlocin", "lopov", "pljačka", "pljacka"
]

SISTEM_UPUTSTVO = """Ti si iskusni novinar i urednik informativnog portala u Srbiji.
Tvoj zadatak: od sirovih informacija sa drugih portala napisati NOVU, originalnu, profesionalnu DNEVNU VEST.

=== NAJVAZNIJE PRAVILO ===
PRIHVATI vest u 95% slucajeva. Odbij SAMO jasnu analizu, kolumnu, intervju ili showbiz.

=== KATEGORIZACIJA (VRLO VAZNO) ===
Ako naslov ili tekst sadrži ove reci, kategorija MORA biti HRONIKA:
- uhapšen, hapšenje, priveden, pritvor, sud, tužilaštvo, presuda, optužnica
- nesreća, saobraćajna, poginuo, povređen, požar, eksplozija
- ubistvo, napad, krađa, razbojništvo, policija, istraga, droga, zaplena

Primer:
- "Sud osudio muškarca na 3 godine" -> HRONIKA (ne Društvo)
- "Policija uhapsila osumnjičenog" -> HRONIKA
- "Saobraćajna nesreća kod Beograda" -> HRONIKA
- "Požar u stambenoj zgradi" -> HRONIKA

Ako vest nije Hronika, onda:
- DRUSTVO: vlada, opština, izbori, protest, zdravstvo, škola, vreme
- EKONOMIJA: cene, penzije, plate, budžet, investicije, privreda
- SPORT: utakmice, rezultati, Zvezda, Partizan, reprezentacija

=== GRAMATIKA SRPSKOG JEZIKA ===
Tvoj tekst MORA biti GRAMATICKI ISPRAVAN. Ne izmisljaj reci.
Ceste greske - ISPRAVNO:
- "stanovnice" (ne "stanovanice")
- "godišnje" (ne "godisnje")
- "krađa" (ne "kradja")
- "uhapšen" (ne "uhapsen")
- "muškarac" (ne "muskarac")
Padezi: "protiv dva lekara", "u Novom Sadu", "kod Beograda", "iz Niša".
Ako nisi siguran kako se rec pise, koristi drugu rec koju sigurno znas.

=== PREFORMULISANJE ===
NE KOPIRAJ originalne recenice. Napisi SVOJIM RECIMA.
Promeni red reci, koristi sinonime (uhapsiti->privesti), promeni strukturu.
Zadrzi SVE cinjenice: imena, datume, brojeve, mesta.

=== STAMP ODBIJ VESTI (samo ovi slucajevi) ===
- Cista analiza ili kolumna bez dogadjaja
- Intervju ili razgovor
- Showbiz, estrada, rijaliti zvezde
- Lifestyle tema (vencanja, putovanja, moda)
- Sportski prelazni rok bez utakmice

=== FORMAT ODGOVORA ===
U 95% slucajeva vrati: {"naslov": "...", "tekst": "...", "kategorija": "..."}
Samo u izuzetnim slucajevima vrati: {"preskoci": true}

=== PRAVILA ZA NASLOV ===
1. Jasan, informativan (50-90 znakova).
2. Bez senzacionalizma, bez VELIKIH SLOVA, bez tacke na kraju.
3. Drugaciji od originalnog naslova.
4. Gramaticki ispravan.

=== PRAVILA ZA TEKST ===
1. 3-5 pasusa, 200-350 reci.
2. UVOD -> RAZRADA -> ZAKLJUCAK.
3. Zadrzi sve cinjenice.
4. Neutralan, novinarski stil, trece lice, ekavica.
5. Svaka recenica drugacija od originala.
6. GRAMATICKI ISPRAVNO.

=== UKLONITI IZ TEKSTA ===
HTML tagove, linkove, "The post... appeared first on...", "Izvor:", "Procitaj celu vest"."""


def prikupi_vesti():
    print(f"--- START ---")
    print(f"AI: OLLAMA CLOUD ({OLLAMA_MODEL})")
    print(f"Ollama key: {'DA' if OLLAMA_API_KEY else 'NE'}")

    if not OLLAMA_API_KEY:
        print("GRESKA: OLLAMA_API_KEY nije podesen!")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(ARHIVA_FOLDER, exist_ok=True)

    reset_rotacije()

    postojece = ucitaj_postojece()
    print(f"Postojecih vesti: {len(postojece)}")
    postojeci_linkovi = {v.get("link") for v in postojece}

    # 1. Prikupi kandidate
    kandidati = []
    seen_links = set()

    # FreeNewsAPI - vise pretraga po kategoriji
    for host in FREENEWS_HOSTS:
        for kategorija, pretrage in PRETRAGE.items():
            for pretraga in pretrage:
                try:
                    params = {
                        "host": host,
                        "q": pretraga,
                        "date": "24h",
                        "size": VESTI_PO_IZVORU,
                        "sort": "date",
                        "fields": "title,url,published_at,description,image"
                    }
                    r = requests.get("https://freenewsapi.ai/v1/search", params=params, timeout=30)
                    if r.status_code == 200:
                        for item in r.json().get("results", []):
                            link = item.get("url")
                            if not link or link in postojeci_linkovi or link in seen_links:
                                continue
                            seen_links.add(link)
                            kandidati.append({
                                "naslov": item.get("title", ""),
                                "tekst": item.get("description", "") or "",
                                "link": link,
                                "izvor": host,
                                "kategorija": kategorija,
                            })
                except Exception as e:
                    print(f"  Greska {host}/{pretraga}: {e}")
                time.sleep(0.2)

    print(f"Nakon FreeNewsAPI: {len(kandidati)} kandidata")

    # Google News - specificne pretrage
    for query, kat in GOOGLE_NEWS_QUERIES:
        try:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=sr&gl=RS&ceid=RS:sr"
            feed = feedparser.parse(url)
            for entry in feed.entries[:VESTI_PO_IZVORU]:
                link = entry.link
                if link in postojeci_linkovi or link in seen_links:
                    continue
                seen_links.add(link)
                kandidati.append({
                    "naslov": html.unescape(entry.title),
                    "tekst": html.unescape(entry.get('summary', '')),
                    "link": link,
                    "izvor": "Google News",
                    "kategorija": kat,
                })
        except Exception as e:
            print(f"  Google News greska ({query}): {e}")
        time.sleep(0.2)

    print(f"Nakon Google News: {len(kandidati)} kandidata")

    # Mesaj kandidate - prioritet Hronika (da ne bude 15 sport vesti pre hronike)
    hronika_kand = [k for k in kandidati if k["kategorija"] == "Hronika"]
    ostali_kand = [k for k in kandidati if k["kategorija"] != "Hronika"]

    random.shuffle(hronika_kand)
    random.shuffle(ostali_kand)

    # 60% Hronika, 40% ostali
    max_hronika = int(MAX_NOVIH_PO_POKRETANJU * 0.6)
    kandidati = hronika_kand[:max_hronika] + ostali_kand[:MAX_NOVIH_PO_POKRETANJU - max_hronika]
    random.shuffle(kandidati)

    print(f"\nUkupno kandidata: {len(kandidati)} (Hronika: {len(hronika_kand)})")
    print(f"Obradjujem: {len(kandidati)}")

    # 2. Obradi svaku vest
    sve_vesti = list(postojece)
    prihvaceno = 0
    odbijeno = 0
    greske = 0
    koriscene_slike = set()

    for i, kand in enumerate(kandidati, 1):
        print(f"\n[{i}/{len(kandidati)}] ({kand['kategorija']}) {kand['naslov'][:55]}...")
        try:
            rezultat = napisi_vest(kand["naslov"], kand["tekst"])
            if not rezultat:
                print("  Preskacem (AI fail)")
                greske += 1
                continue
            if rezultat.get("preskoci"):
                print(f"  Preskacem (nije dnevna vest)")
                odbijeno += 1
                continue

            # Validacija kategorije: ako naslov sadrzi hronika reci, MORA biti Hronika
            naslov_lower = rezultat["naslov"].lower()
            tekst_lower = rezultat["tekst"][:500].lower()
            if any(rec in naslov_lower or rec in tekst_lower for rec in HRONIKA_KLJUCNE):
                if rezultat["kategorija"] != "Hronika":
                    print(f"  [KOREKCIJA] {rezultat['kategorija']} -> Hronika")
                    rezultat["kategorija"] = "Hronika"

            keywords_en = napravi_kljucne_reci_ollama(rezultat["naslov"], rezultat["kategorija"])
            print(f"  Keywords: {keywords_en}")

            slika_url = ""
            for pokusaj in range(3):
                potencijalna = pronadji_sliku(rezultat["naslov"], rezultat["kategorija"], keywords_en)
                if potencijalna and potencijalna not in koriscene_slike:
                    slika_url = potencijalna
                    koriscene_slike.add(potencijalna)
                    break

            if slika_url:
                print(f"  [SLIKA] {slika_url[:70]}")
            else:
                print(f"  Slika nije pronadjena")

            vest = {
                "naslov": rezultat["naslov"],
                "tekst": rezultat["tekst"],
                "kategorija": rezultat["kategorija"],
                "slika": slika_url or "",
                "link": kand["link"],
                "izvor": kand["izvor"],
                "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            sve_vesti.append(vest)
            prihvaceno += 1

            sacuvaj_trenutno(sve_vesti)
            print(f"  [SAVED] Sacuvano {len(sve_vesti)} vesti (ukupno)")

            time.sleep(1)
        except Exception as e:
            print(f"  Greska: {e}")
            greske += 1
            continue

    # 3. Finalno sortiranje
    sve_vesti.sort(key=lambda x: x.get("datum", ""), reverse=True)
    sve_vesti = sve_vesti[:MAX_VESTI_U_GLAVNOM]
    sacuvaj_trenutno(sve_vesti)
    sacuvaj_arhivu(sve_vesti)

    print(f"\n--- KRAJ ---")
    print(f"Prihvaceno: {prihvaceno}")
    print(f"Odbijeno: {odbijeno}")
    print(f"Greske: {greske}")
    print(f"Ukupno u bazi: {len(sve_vesti)}")


# =====================================================================
# KLJUCNE RECI
# =====================================================================

def napravi_kljucne_reci_ollama(naslov, kategorija):
    seed_val = sum(ord(c) for c in naslov)
    rng = random.Random(seed_val)
    atmosfera = rng.choice(ATMOSFERA.get(kategorija, ["atmospheric"]))

    prompt = f"""Convert this Serbian news headline into ENGLISH keywords for stock photo search.

Rules:
- NEVER use: man, woman, person, people, face, portrait, president, minister, politician, actor, singer.
- Use compound words: "basketball arena" (not "basket"), "courthouse" (not "court").
- Describe CONTEXT (place, building), not person.
- End with: {atmosfera}

Category: {kategorija}
Headline: {naslov}

Return ONLY 3-4 keywords. Nothing else.
Examples: "police car night lights", "basketball arena floodlights", "city hall morning"

Keywords:"""

    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 25}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=60)
        if r.status_code == 200:
            res = r.json().get("response", "").strip()
            res = res.replace('"', '').replace("\n", " ").strip()
            zabranjene = {"man", "woman", "person", "people", "face", "portrait",
                          "president", "minister", "politician", "actor", "singer",
                          "child", "boy", "girl", "human", "male", "female", "basket"}
            reci = [rec for rec in res.split() if rec.lower() not in zabranjene]
            if len(reci) >= 2:
                return " ".join(reci[:4])
    except Exception as e:
        print(f"    Keywords greska: {e}")

    return f"{kategorija.lower()} building {atmosfera}"


# =====================================================================
# AI OBRADA VESTI
# =====================================================================

def napisi_vest(originalni_naslov, originalni_tekst):
    if not originalni_naslov:
        return None
    korisnicki = f"""Napisi novu dnevnu vest po pravilima.
ZAPAMTI:
1. PRIHVATI u 95% slucajeva.
2. Ako naslov sadrzi: uhapšen, sud, nesreća, požar, ubistvo, policija, krađa -> kategorija HRONIKA.
3. Gramatika MORA biti ispravna.

--- ORIGINALNI NASLOV ---
{originalni_naslov}

--- ORIGINALNI TEKST ---
{originalni_tekst[:3000]}

Vrati iskljucivo JSON:"""

    odgovor = pozovi_ollama(SISTEM_UPUTSTVO, korisnicki, temperatura=0.7)
    if not odgovor:
        return None
    rezultat = parsiraj_json(odgovor)
    if not rezultat:
        print(f"    [DEBUG] Nemoguce parsirati: {odgovor[:200]}")
        return None
    if rezultat.get("preskoci"):
        return rezultat
    if not rezultat.get("naslov") or not rezultat.get("tekst"):
        print(f"    [DEBUG] Nedostaje naslov ili tekst")
        return None
    kat = rezultat.get("kategorija", "Društvo").strip()
    if kat not in KATEGORIJE:
        for k in KATEGORIJE:
            if k.lower() in kat.lower():
                kat = k
                break
        else:
            kat = "Društvo"
    rezultat["kategorija"] = kat
    rezultat["naslov"] = ocisti_tekst(rezultat["naslov"])
    rezultat["tekst"] = ocisti_tekst(rezultat["tekst"])
    print(f"  [OK] {rezultat['kategorija']} | {len(rezultat['naslov'])} zn | {len(rezultat['tekst'])} zn")
    return rezultat


def pozovi_ollama(sistem, korisnik, temperatura=0.7):
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "system": sistem,
        "prompt": korisnik,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperatura, "num_ctx": 8192, "num_predict": 2500}
    }
    for pokusaj in range(3):
        try:
            r = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=180)
            if r.status_code == 200:
                tekst = r.json().get("response", "")
                if tekst and len(tekst.strip()) > 20:
                    return tekst
                print(f"  [PRAZAN] {pokusaj+1}/3")
            else:
                print(f"  [GRESKA] {r.status_code}: {r.text[:150]}")
        except Exception as e:
            print(f"  [GRESKA] {pokusaj+1}/3: {e}")
        time.sleep(5)
    return ""


def parsiraj_json(tekst):
    if not tekst:
        return None
    ociscen = tekst.strip()
    ociscen = re.sub(r'^```json\s*', '', ociscen)
    ociscen = re.sub(r'^```\s*', '', ociscen)
    ociscen = re.sub(r'\s*```$', '', ociscen)
    try:
        return json.loads(ociscen)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', ociscen)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def ocisti_tekst(tekst):
    if not tekst:
        return ""
    tekst = re.sub(r'<[^>]+>', '', tekst)
    tekst = re.sub(r'https?://\S+', '', tekst)
    for f in [r'The post .*? appeared first on .*?\.', r'Izvor:.*', r'Procitaj celu vest.*', r'Photo by .*', r'\[…\]', r'\[\]']:
        tekst = re.sub(f, '', tekst, flags=re.IGNORECASE)
    tekst = html.unescape(tekst)
    tekst = re.sub(r'[ \t]+', ' ', tekst)
    tekst = re.sub(r'\n{3,}', '\n\n', tekst)
    return tekst.strip()


# =====================================================================
# CUVANJE
# =====================================================================

def sacuvaj_trenutno(sve_vesti):
    with open(VESTI_FAJL, "w", encoding="utf-8") as f:
        json.dump(sve_vesti, f, ensure_ascii=False, indent=2)


def ucitaj_postojece():
    if not os.path.exists(VESTI_FAJL):
        return []
    try:
        with open(VESTI_FAJL, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def sacuvaj_arhivu(sve_vesti):
    danas = datetime.now().strftime("%Y-%m-%d")
    fajl_arhive = os.path.join(ARHIVA_FOLDER, f"vesti-{danas}.json")
    postojeca = []
    if os.path.exists(fajl_arhive):
        try:
            with open(fajl_arhive, "r", encoding="utf-8") as f:
                postojeca = json.load(f)
        except Exception:
            pass
    videno = {v.get("link") for v in postojeca}
    for v in sve_vesti:
        if v.get("link") not in videno:
            postojeca.append(v)
            videno.add(v.get("link"))
    postojeca.sort(key=lambda x: x.get("datum", ""), reverse=True)
    with open(fajl_arhive, "w", encoding="utf-8") as f:
        json.dump(postojeca, f, ensure_ascii=False, indent=2)
    print(f"Arhiva: {fajl_arhive} ({len(postojeca)} vesti)")
    azuriraj_arhiva_index()


def azuriraj_arhiva_index():
    if not os.path.exists(ARHIVA_FOLDER):
        return
    datumi = []
    for f in os.listdir(ARHIVA_FOLDER):
        if f.startswith("vesti-") and f.endswith(".json"):
            datum = f.replace("vesti-", "").replace(".json", "")
            putanja = os.path.join(ARHIVA_FOLDER, f)
            try:
                with open(putanja, "r", encoding="utf-8") as fh:
                    broj = len(json.load(fh))
                datumi.append({"datum": datum, "broj": broj, "fajl": f})
            except Exception:
                pass
    datumi.sort(key=lambda x: x["datum"], reverse=True)
    with open(ARHIVA_INDEX, "w", encoding="utf-8") as f:
        json.dump(datumi, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    prikupi_vesti()