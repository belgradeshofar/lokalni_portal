import feedparser
import os
import json
import time
import requests
import html
import re
import urllib.parse
from datetime import datetime

# =====================================================================
# KONFIGURACIJA
# =====================================================================

# Ollama Cloud
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_URL = "https://ollama.com/api/generate"
OLLAMA_MODEL = "gemma4:31b-cloud" # Besplatan model na Ollama Cloud-u

# FreeNewsAPI (besplatan, bez kljuca)
FREENEWS_HOSTS = [
    "www.kurir.rs",
    "www.novosti.rs",
    "www.alo.rs",
    "n1info.rs",
]

# Google News RSS upiti
GOOGLE_NEWS_QUERIES = [
    "hronika",
    "društvo",
    "ekonomija",
    "sport",
]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
ARHIVA_FOLDER = os.path.join(OUTPUT_FOLDER, "arhiva")
ARHIVA_INDEX = os.path.join(ARHIVA_FOLDER, "index.json")
SLIKE_FOLDER = os.path.join(OUTPUT_FOLDER, "slike")

MAX_VESTI_U_GLAVNOM = 200
MAX_NOVIH_PO_POKRETANJU = 40 # Povecano na 40
VESTI_PO_IZVORU = 10 # Uzimamo do 10 vesti po izvoru

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KATEGORIJE = ["Hronika", "Društvo", "Ekonomija", "Sport"]

# Kljucne reci za filtriranje
KLJUCNE_RECI = {
    "Hronika": [
        "hapšenje", "uhapšen", "priveden", "sud", "tužilaštvo", "presuda",
        "nesreća", "saobraćajna", "požar", "eksplozija", "napad", "ubistvo",
        "krađa", "razbojništvo", "policija", "mup", "istraga", "zločin",
        "kriminal", "droga", "oružje", "pritvor", "optužnica"
    ],
    "Društvo": [
        "vlada", "ministarstvo", "opština", "grad", "skupština", "izbori",
        "protest", "manifestacija", "obeležavanje", "vremenska", "poplava",
        "sneg", "oluja", "vrućina", "zdravstvo", "obrazovanje", "škola",
        "fakultet", "studenti", "gradjani", "lokalna", "samouprava"
    ],
    "Ekonomija": [
        "cena", "dinara", "evra", "inflacija", "plata", "penzija", "budžet",
        "investicija", "fabrika", "kompanija", "privreda", "poljoprivreda",
        "turizam", "sajam", "izvoz", "uvoz", "porez", "subvencija", "kredit"
    ],
    "Sport": [
        "utakmica", "pobeda", "poraz", "rezultat", "gol", "koš", "tenis",
        "fudbal", "košarka", "odbojka", "rukomet", "atletika", "olimpijada",
        "medalja", "prvenstvo", "liga", "kup", "reprezentacija", "klub",
        "igrač", "trener", "stadion", "takmičenje"
    ],
}

# =====================================================================
# AI PROMPT
# =====================================================================

SISTEM_UPUTSTVO = """Ti si iskusni novinar i urednik informativnog portala u Srbiji.
Tvoj zadatak: od sirovih informacija sa drugih portala napraviti NOVU, originalnu, profesionalnu DNEVNU VEST.

=== STA PRIHVATAMO (DNEVNE VESTI) ===
- Hronika: saobracajne nesrece, hapsenja, sudjenja, pozari, nesrece, kradje
- Dnevni dogadjaji: izbori, protesti, skupovi, manifestacije, obelezavanja
- Sluzbena saopstenja: vlada, opstine, institucije, ministarstva
- Vremenske nepogode: poplave, oluje, sneg, vrucine
- Sportski rezultati: utakmice, takmicenja, medalje
- Vesti od javnog znacaja: cene, saobracaj, infrastruktura, zdravstvo

=== STA NE PRIHVATAMO (NOVINSKI CLANCI) ===
- Izjave politicara tipa "Vucic je rekao...", "opozicija tvrdi..."
- Analize, komentari, kolumne, misljenja
- Intervjui i razgovori
- Predizborne kampanje i politicke svadje
- "Ko je sta rekao" vesti
- Ljudske price i lifestyle teme
- Showbiz, estrada, rijaliti

AKO JE ORIGINALNA VEST TIPA "NE PRIHVATAMO", vrati ISKLJUCIVO:
{"preskoci": true}

=== PRAVILA ZA NASLOV (ako prihvatas) ===
1. Jasan, informativan, privlacan. Citalac odmah zna o cemu je vest.
2. Duzina: 50-90 znakova.
3. Bez senzacionalizma, bez CLICKBAIT-a, bez VELIKIH SLOVA (osim akronima).
4. Bez tacke na kraju naslova.
5. Pravilna gramatika, padezi, slaganje.
6. Ako je original naslov prekratak, prosiri ga kontekstom iz teksta.

=== PRAVILA ZA TEKST ===
1. Duzina: 3-5 pasusa, ukupno 200-350 reci.
2. Struktura klasicne novinske vesti:
   - UVOD: KO, STA, GDE, KADA, ZASTO.
   - RAZRADA: detalji, imena, brojevi, datumi, mesta.
   - ZAKLJUCAK: znacaj za gradjane ili sta sledi.
3. Zadrzi SVE cinjenice iz originala.
4. NEMA izmisljanja.
5. Neutralan, novinarski stil u trecem licu.
6. Pisi na srpskom jeziku (ekavica).

=== STROGO UKLONITI ===
1. HTML tagove i linkove.
2. Fraze "The post... appeared first on...", "Izvor:", "Procitaj celu vest".
3. Ponavljanja.
4. Originalne fraze iz druge vesti.
5. Pominjanje AI-ja, modela, generisanja.
6. Fraze "klikni", "podeli", "lajkuj".

=== FORMAT ODGOVORA ===
Ako prihvatas vest, vrati ISKLJUCIVO JSON:
{"naslov": "...", "tekst": "...", "kategorija": "..."}

Ako odbijas vest, vrati:
{"preskoci": true}

Kategorija mora biti JEDNA od: Hronika, Drustvo, Ekonomija, Sport."""

# =====================================================================
# GLAVNA FUNKCIJA
# =====================================================================

def prikupi_vesti():
    print(f"--- START ---")
    print(f"Aktivni AI: OLLAMA CLOUD ({OLLAMA_MODEL})")
    print(f"Ollama API key prisutan: {'DA' if OLLAMA_API_KEY else 'NE'}")

    if not OLLAMA_API_KEY:
        print("GRESKA: OLLAMA_API_KEY nije podesen!")
        return

    postojece = ucitaj_postojece()
    print(f"Postojecih vesti u bazi: {len(postojece)}")
    postojeci_linkovi = {v.get("link") for v in postojece}

    kandidati = []

    # 1. FreeNewsAPI
    for host in FREENEWS_HOSTS:
        for kategorija, reci in KLJUCNE_RECI.items():
            print(f"Dohvatam sa {host} za kategoriju: {kategorija}...")
            try:
                # Uzimamo 3 kljucne reci za pretragu
                q = " ".join(reci[:3])
                params = {
                    "host": host,
                    "q": q,
                    "date": "24h",
                    "size": VESTI_PO_IZVORU,
                    "sort": "date",
                    "fields": "title,url,published_at,description,image",
                }
                r = requests.get("https://freenewsapi.ai/v1/search", params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get("results", []):
                        link = item.get("url")
                        if link in postojeci_linkovi:
                            continue
                        kandidati.append({
                            "naslov": item.get("title", ""),
                            "tekst": item.get("description", "") or "",
                            "link": link,
                            "izvor": host,
                            "slika_url": item.get("image"),
                            "kategorija": kategorija,
                        })
                    print(f"  Pronadeno: {len(data.get('results', []))}")
                else:
                    print(f"  Greska: {r.status_code}")
            except Exception as e:
                print(f"  Greska: {e}")
            time.sleep(0.5)

    # 2. Google News RSS
    for query in GOOGLE_NEWS_QUERIES:
        print(f"Dohvatam Google News za: {query}...")
        try:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=sr&gl=RS&ceid=RS:sr"
            feed = feedparser.parse(url)
            for entry in feed.entries[:VESTI_PO_IZVORU]:
                link = entry.link
                if link in postojeci_linkovi:
                    continue
                # Kategorija na osnovu upita
                kat = "Hronika"
                if "društvo" in query:
                    kat = "Društvo"
                elif "ekonomija" in query:
                    kat = "Ekonomija"
                elif "sport" in query:
                    kat = "Sport"
                kandidati.append({
                    "naslov": html.unescape(entry.title),
                    "tekst": html.unescape(entry.get('summary', '')),
                    "link": link,
                    "izvor": "Google News",
                    "slika_url": None,
                    "kategorija": kat,
                })
            print(f"  Pronadeno: {len(feed.entries[:VESTI_PO_IZVORU])}")
        except Exception as e:
            print(f"  Greska: {e}")
        time.sleep(0.5)

    print(f"\nUkupno novih kandidata: {len(kandidati)}")
    kandidati = kandidati[:MAX_NOVIH_PO_POKRETANJU]
    print(f"Obradjujem prvih: {len(kandidati)}")

    nove_vesti = []
    for i, kand in enumerate(kandidati, 1):
        print(f"\n[{i}/{len(kandidati)}] {kand['naslov'][:60]}...")
        try:
            rezultat = napisi_vest(kand["naslov"], kand["tekst"])
            if not rezultat:
                print("  Preskacem (AI nije vratio rezultat)")
                continue
            if rezultat.get("preskoci"):
                print(f"  Preskacem (nije dnevna vest)")
                continue

            ime_slike = generisi_sliku_pollinations(rezultat["naslov"], rezultat["kategorija"])

            vest = {
                "naslov": rezultat["naslov"],
                "tekst": rezultat["tekst"],
                "kategorija": rezultat["kategorija"],
                "slika": ime_slike,
                "link": kand["link"],
                "izvor": kand["izvor"],
                "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            nove_vesti.append(vest)
            time.sleep(2)
        except Exception as e:
            print(f"  Greska: {e}")
            continue

    print(f"\nNovih vesti uspesno: {len(nove_vesti)}")

    sve = nove_vesti + postojece
    videno = set()
    unikatne = []
    for v in sve:
        link = v.get("link", "")
        if link and link not in videno:
            videno.add(link)
            unikatne.append(v)

    unikatne.sort(key=lambda x: x.get("datum", ""), reverse=True)
    finalne = unikatne[:MAX_VESTI_U_GLAVNOM]

    os.makedirs(SLIKE_FOLDER, exist_ok=True)
    os.makedirs(ARHIVA_FOLDER, exist_ok=True)

    with open(VESTI_FAJL, "w", encoding="utf-8") as f:
        json.dump(finalne, f, ensure_ascii=False, indent=2)
    print(f"\nSacuvano {len(finalne)} vesti u {VESTI_FAJL}")

    sacuvaj_arhivu(finalne)

    print(f"\n--- KRAJ ---")

# =====================================================================
# AI OBRADA
# =====================================================================

def napisi_vest(originalni_naslov, originalni_tekst):
    if not originalni_naslov:
        return None
    korisnicki = f"""Napravi novu dnevnu vest po pravilima iz sistemskog uputstva.

--- ORIGINALNI NASLOV ---
{originalni_naslov}

--- ORIGINALNI TEKST ---
{originalni_tekst[:3000]}

Vrati iskljucivo JSON:"""
    odgovor = pozovi_ollama(SISTEM_UPUTSTVO, korisnicki)
    if not odgovor:
        return None
    rezultat = parsiraj_json(odgovor)
    if not rezultat:
        return None
    if rezultat.get("preskoci"):
        return rezultat
    if not rezultat.get("naslov") or not rezultat.get("tekst"):
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
    print(f"  [OK] {rezultat['kategorija']} | {len(rezultat['naslov'])} zn naslov | {len(rezultat['tekst'])} zn tekst")
    return rezultat

def pozovi_ollama(sistem, korisnik):
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OLLAMA_MODEL,
        "system": sistem,
        "prompt": korisnik,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.85, "num_ctx": 8192, "num_predict": 2500},
    }
    for pokusaj in range(3):
        try:
            r = requests.post(OLLAMA_URL, json=payload, headers=headers, timeout=180)
            if r.status_code == 200:
                tekst = r.json().get("response", "")
                if tekst and len(tekst.strip()) > 20:
                    return tekst
                print(f"  [PRAZAN] Pokusaj {pokusaj+1}/3")
            else:
                print(f"  [GRESKA] Ollama status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  [GRESKA] Pokusaj {pokusaj+1}/3: {e}")
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
    for f in [
        r'The post .*? appeared first on .*?\.',
        r'Izvor:.*',
        r'Procitaj celu vest.*',
        r'Photo by .*',
        r'\[…\]', r'\[\]',
    ]:
        tekst = re.sub(f, '', tekst, flags=re.IGNORECASE)
    tekst = html.unescape(tekst)
    tekst = re.sub(r'[ \t]+', ' ', tekst)
    tekst = re.sub(r'\n{3,}', '\n\n', tekst)
    return tekst.strip()

# =====================================================================
# SLIKE
# =====================================================================

def generisi_sliku_pollinations(naslov, kategorija):
    if not naslov:
        return ""
    prompt_baza = {
        "Hronika": "empty street at night, blue police lights, moody fog",
        "Društvo": "city street, morning fog, moody atmosphere",
        "Ekonomija": "industrial buildings, factory, dusk sky",
        "Sport": "empty stadium, sports field, dramatic floodlights",
    }
    baza = prompt_baza.get(kategorija, "small town, morning fog, atmospheric")
    finalni = f"{baza}, no people, no faces, cinematic, atmospheric, landscape, 4k, photorealistic"
    encoded = urllib.parse.quote(finalni)
    url = "https://image.pollinations.ai/prompt/" + encoded
    params = {
        "width": 800, "height": 500, "nologo": "true", "model": "flux", "seed": int(time.time()),
    }
    ime_fajla = f"slika_{int(time.time()*1000)}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    for pokusaj in range(3):
        try:
            print(f"    Generisem sliku (pokusaj {pokusaj+1}/3)...")
            r = requests.get(url, params=params, timeout=120)
            content_type = r.headers.get("content-type", "")
            if r.status_code == 200 and "image" in content_type:
                with open(putanja, "wb") as f:
                    f.write(r.content)
                print(f"    [SLIKA] OK: {ime_fajla}")
                return ime_fajla
            elif r.status_code == 402:
                print(f"    [402] Rate limit, cekam 30s...")
                time.sleep(30)
            else:
                print(f"    [GRESKA] Status {r.status_code}, tip {content_type}")
                time.sleep(10)
        except Exception as e:
            print(f"    [GRESKA] {e}")
            time.sleep(10)
    print(f"    Slika nije generisana.")
    return ""

# =====================================================================
# ARHIVA
# =====================================================================

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
    postojeca_arhiva = []
    if os.path.exists(fajl_arhive):
        try:
            with open(fajl_arhive, "r", encoding="utf-8") as f:
                postojeca_arhiva = json.load(f)
        except Exception:
            pass
    videno = {v.get("link") for v in postojeca_arhiva}
    for v in sve_vesti:
        if v.get("link") not in videno:
            postojeca_arhiva.append(v)
            videno.add(v.get("link"))
    postojeca_arhiva.sort(key=lambda x: x.get("datum", ""), reverse=True)
    with open(fajl_arhive, "w", encoding="utf-8") as f:
        json.dump(postojeca_arhiva, f, ensure_ascii=False, indent=2)
    print(f"Arhiva sacuvana: {fajl_arhive} ({len(postojeca_arhiva)} vesti)")
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