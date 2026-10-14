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
GOOGLE_NEWS_QUERIES = ["hronika", "društvo", "ekonomija", "sport"]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
ARHIVA_FOLDER = os.path.join(OUTPUT_FOLDER, "arhiva")
ARHIVA_INDEX = os.path.join(ARHIVA_FOLDER, "index.json")

MAX_VESTI_U_GLAVNOM = 200
MAX_NOVIH_PO_POKRETANJU = 40
VESTI_PO_IZVORU = 10

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KATEGORIJE = ["Hronika", "Društvo", "Ekonomija", "Sport"]

KLJUCNE_RECI = {
    "Hronika": ["hapšenje", "uhapšen", "priveden", "sud", "tužilaštvo", "presuda", "nesreća", "saobraćajna", "požar", "eksplozija", "napad", "ubistvo", "krađa", "razbojništvo", "policija", "mup", "istraga", "zločin", "kriminal"],
    "Društvo": ["vlada", "ministarstvo", "opština", "grad", "skupština", "izbori", "protest", "manifestacija", "obeležavanje", "vremenska", "poplava", "sneg", "oluja", "vrućina", "zdravstvo", "obrazovanje", "škola", "fakultet", "studenti"],
    "Ekonomija": ["cena", "dinara", "evra", "inflacija", "plata", "penzija", "budžet", "investicija", "fabrika", "kompanija", "privreda", "poljoprivreda", "turizam", "sajam", "izvoz", "uvoz", "porez"],
    "Sport": ["crvena zvezda", "partizan", "reprezentacija", "derbi", "olimpijada", "svetsko prvenstvo"],
}

ATMOSFERA = {
    "Hronika": ["night", "dusk", "foggy", "dark"],
    "Društvo": ["morning", "dawn", "afternoon", "autumn"],
    "Ekonomija": ["dusk", "industrial", "morning", "sunset"],
    "Sport": ["floodlights", "night", "dramatic", "stadium"],
}

SISTEM_UPUTSTVO = """Ti si iskusni novinar i urednik informativnog portala u Srbiji.
Tvoj zadatak: od sirovih informacija sa drugih portala napisati NOVU, originalnu, profesionalnu DNEVNU VEST.

=== NAJVAZNIJE PRAVILO ===
AKO NISI 100% SIGURAN DA VEST TREBA ODBITI, PRIHVATI JE.
Bolje prihvatiti 10 losih nego odbiti 1 dobru.

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

=== STAMP PRIHVATI VESTI ===
U 99% slucajeva PRIHVATI vest. ODBIJ SAMO ako je jasno:
- Cista analiza ili kolumna bez dogadjaja
- Intervju ili razgovor
- Showbiz, estrada, rijaliti zvezde
- Lifestyle tema (vencanja, putovanja, moda)
- Sportski prelazni rok bez utakmice

=== STAMP ODBIJ VESTI ===
Ako je vest: hapsenje, sud, nesreca, pozar, sudar, utakmica, izbori, vlada,
cene, vreme, poplava, požar, ubistvo, kradja, protest, manifestacija -> PRIHVATI.

=== FORMAT ODGOVORA ===
U 99% slucajeva vrati: {"naslov": "...", "tekst": "...", "kategorija": "..."}
Samo u izuzetnim slucajevima vrati: {"preskoci": true}

Kategorija: Hronika, Drustvo, Ekonomija ili Sport.

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
    for host in FREENEWS_HOSTS:
        for kategorija, reci in KLJUCNE_RECI.items():
            print(f"Dohvatam: {host} / {kategorija}...")
            try:
                q = " ".join(reci[:3])
                params = {"host": host, "q": q, "date": "24h", "size": VESTI_PO_IZVORU, "sort": "date", "fields": "title,url,published_at,description,image"}
                r = requests.get("https://freenewsapi.ai/v1/search", params=params, timeout=30)
                if r.status_code == 200:
                    for item in r.json().get("results", []):
                        link = item.get("url")
                        if link in postojeci_linkovi:
                            continue
                        kandidati.append({
                            "naslov": item.get("title", ""),
                            "tekst": item.get("description", "") or "",
                            "link": link,
                            "izvor": host,
                            "kategorija": kategorija,
                        })
            except Exception as e:
                print(f"  Greska: {e}")
            time.sleep(0.3)

    for query in GOOGLE_NEWS_QUERIES:
        print(f"Dohvatam: Google News / {query}...")
        try:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=sr&gl=RS&ceid=RS:sr"
            feed = feedparser.parse(url)
            for entry in feed.entries[:VESTI_PO_IZVORU]:
                link = entry.link
                if link in postojeci_linkovi:
                    continue
                kat = {"hronika": "Hronika", "društvo": "Društvo", "ekonomija": "Ekonomija", "sport": "Sport"}.get(query, "Društvo")
                kandidati.append({
                    "naslov": html.unescape(entry.title),
                    "tekst": html.unescape(entry.get('summary', '')),
                    "link": link,
                    "izvor": "Google News",
                    "kategorija": kat,
                })
        except Exception as e:
            print(f"  Greska: {e}")
        time.sleep(0.3)

    print(f"\nUkupno kandidata: {len(kandidati)}")
    kandidati = kandidati[:MAX_NOVIH_PO_POKRETANJU]
    print(f"Obradjujem: {len(kandidati)}")

    # 2. Obradi svaku vest
    sve_vesti = list(postojece)
    prihvaceno = 0
    odbijeno = 0
    greske = 0
    koriscene_slike = set()

    for i, kand in enumerate(kandidati, 1):
        print(f"\n[{i}/{len(kandidati)}] {kand['naslov'][:60]}...")
        try:
            rezultat = napisi_vest(kand["naslov"], kand["tekst"])
            if not rezultat:
                print("  Preskacem (AI fail)")
                greske += 1
                continue
            if rezultat.get("preskoci"):
                print(f"  Preskacem (nije dnevna vest): {kand['naslov'][:60]}")
                odbijeno += 1
                continue

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
                print(f"  [SLIKA] {slika_url[:80]}")
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
ZAPAMTI: PRIHVATI u 99% slucajeva. Odbij samo jasnu analizu/intervju/showbiz.
Gramatika MORA biti ispravna.

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