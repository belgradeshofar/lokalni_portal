import feedparser
import os
import json
import time
import requests
import html
import re
from datetime import datetime, timedelta

# =====================================================================
# KONFIGURACIJA
# =====================================================================

# Automatski prepoznaje gde se izvrsava:
# - GitHub Actions -> Gemini (nema RAM-a za Zora)
# - Lokalno -> Zora preko Ollama
USE_OLLAMA = os.environ.get("GITHUB_ACTIONS") != "true"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "olivilo/zora:v1.12-q8"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

# Svi feedovi koji su prosli test
RSS_FEEDS = [
    ("Kurir", "https://www.kurir.rs/rss/vesti/"),
    ("Novosti", "https://www.novosti.rs/rss/2-Sve%20vesti"),
    ("Alo", "https://www.alo.rs/rss/"),
    ("Telegraf", "https://www.telegraf.rs/rss/vesti"),
    ("Danas", "https://www.danas.rs/feed/"),
    ("N1", "https://n1info.rs/feed/"),
    ("Blic", "https://news.google.com/rss/search?q=site:blic.rs&hl=sr&gl=RS&ceid=RS:sr"),
]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
ARHIVA_FOLDER = os.path.join(OUTPUT_FOLDER, "arhiva")
ARHIVA_INDEX = os.path.join(ARHIVA_FOLDER, "index.json")
SLIKE_FOLDER = os.path.join(OUTPUT_FOLDER, "slike")

# Koliko ukupno vesti cuvamo u glavnom fajlu (najnovije)
MAX_VESTI_U_GLAVNOM = 100
# Koliko najvise novih vesti obradjujemo u jednom pokretanju
MAX_NOVIH_PO_POKRETANJU = 12
# Koliko vesti uzimamo po jednom feedu
VESTI_PO_FEEDU = 5

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KATEGORIJE = ["Politika", "Hronika", "Sport", "Ekonomija", "Društvo", "Svet"]


# =====================================================================
# AI PROMPT
# =====================================================================

SISTEM_UPUTSTVO = """Ti si iskusni novinar i urednik informativnog portala u Srbiji.
Tvoj zadatak: od sirovih informacija sa drugih portala napraviti NOVU, originalnu, profesionalnu novinsku vest.

=== PRAVILA ZA NASLOV ===
1. Jasan, informativan, privlacan. Citalac odmah zna o cemu je vest.
2. Duzina: 50-90 znakova.
3. Bez senzacionalizma, bez CLICKBAIT-a, bez VELIKIH SLOVA (osim akronima).
4. Bez znaka pitanja i uzbucnika, osim u izuzetnim slucajevima.
5. Bez tacke na kraju naslova.
6. Pravilna gramatika, padezi, slaganje.
7. Ako je original naslov prekratak, prosiri ga kontekstom iz teksta.

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
Vrati ISKLJUCIVO JSON:
{"naslov": "...", "tekst": "...", "kategorija": "..."}

Kategorija mora biti JEDNA od: Politika, Hronika, Sport, Ekonomija, Drustvo, Svet."""


# =====================================================================
# GLAVNA FUNKCIJA
# =====================================================================

def prikupi_vesti():
    print(f"--- START ---")
    print(f"Aktivni AI: {'ZORA (Ollama)' if USE_OLLAMA else 'GEMINI'}")
    
    # 1. Ucitaj postojece vesti
    postojece = ucitaj_postojece()
    print(f"Postojecih vesti u bazi: {len(postojece)}")
    postojeci_linkovi = {v.get("link") for v in postojece}
    
    # 2. Prikupi nove iz svih feedova
    kandidati = []
    for naziv, url in RSS_FEEDS:
        print(f"\nPovezujem se na: {naziv} ({url})...")
        try:
            feed = feedparser.parse(url)
            if feed.bozo or not feed.entries:
                print(f"  Nema vesti.")
                continue
            
            broj = 0
            for entry in feed.entries[:VESTI_PO_FEEDU]:
                link = entry.link
                if link in postojeci_linkovi:
                    continue
                
                originalni_naslov = html.unescape(entry.title)
                originalni_tekst = html.unescape(entry.get('summary', entry.get('description', '')))
                
                kandidati.append({
                    "naslov": originalni_naslov,
                    "tekst": originalni_tekst,
                    "link": link,
                    "izvor": naziv,
                    "entry": entry,
                })
                broj += 1
            
            print(f"  Novih kandidata: {broj}")
        except Exception as e:
            print(f"  Greska: {e}")
            continue
    
    print(f"\nUkupno novih kandidata: {len(kandidati)}")
    
    # 3. Ogranici na MAX_NOVIH_PO_POKRETANJU
    kandidati = kandidati[:MAX_NOVIH_PO_POKRETANJU]
    print(f"Obradjujem prvih: {len(kandidati)}")
    
    # 4. Obradi svaki kandidat
    nove_vesti = []
    for i, kand in enumerate(kandidati, 1):
        print(f"\n[{i}/{len(kandidati)}] {kand['naslov'][:60]}...")
        try:
            # AI obrada
            rezultat = napisi_vest(kand["naslov"], kand["tekst"])
            if not rezultat:
                print("  Preskacem (AI nije vratio rezultat)")
                continue
            
            # Slika
            ime_slike = nadji_sliku(rezultat["naslov"], rezultat["kategorija"], kand["entry"])
            
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
    
    # 5. Spoji sa postojecim
    sve = nove_vesti + postojece
    # Ukloni duplikate po linku
    videno = set()
    unikatne = []
    for v in sve:
        link = v.get("link", "")
        if link and link not in videno:
            videno.add(link)
            unikatne.append(v)
    
    # Sortiraj po datumu (najnovije prvo)
    unikatne.sort(key=lambda x: x.get("datum", ""), reverse=True)
    
    # Ogranici
    finalne = unikatne[:MAX_VESTI_U_GLAVNOM]
    
    # 6. Sacuvaj
    os.makedirs(SLIKE_FOLDER, exist_ok=True)
    os.makedirs(ARHIVA_FOLDER, exist_ok=True)
    
    with open(VESTI_FAJL, "w", encoding="utf-8") as f:
        json.dump(finalne, f, ensure_ascii=False, indent=2)
    print(f"\nSacuvano {len(finalne)} vesti u {VESTI_FAJL}")
    
    # 7. Sacuvaj dnevnu arhivu
    sacuvaj_arhivu(finalne)
    
    print(f"\n--- KRAJ ---")


# =====================================================================
# ARHIVA
# =====================================================================

def ucitaj_postojece():
    """Ucitava postojece vesti iz vesti.json."""
    if not os.path.exists(VESTI_FAJL):
        return []
    try:
        with open(VESTI_FAJL, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Greska pri ucitavanju: {e}")
        return []


def sacuvaj_arhivu(sve_vesti):
    """Cuva dnevnu arhivu i azurira index."""
    danas = datetime.now().strftime("%Y-%m-%d")
    fajl_arhive = os.path.join(ARHIVA_FOLDER, f"vesti-{danas}.json")
    
    # Ucitaj postojecu arhivu za danas (ako postoji) i spoji
    postojeca_arhiva = []
    if os.path.exists(fajl_arhive):
        try:
            with open(fajl_arhive, "r", encoding="utf-8") as f:
                postojeca_arhiva = json.load(f)
        except Exception:
            pass
    
    # Merge
    videno = {v.get("link") for v in postojeca_arhiva}
    for v in sve_vesti:
        if v.get("link") not in videno:
            postojeca_arhiva.append(v)
            videno.add(v.get("link"))
    
    # Sortiraj
    postojeca_arhiva.sort(key=lambda x: x.get("datum", ""), reverse=True)
    
    with open(fajl_arhive, "w", encoding="utf-8") as f:
        json.dump(postojeca_arhiva, f, ensure_ascii=False, indent=2)
    print(f"Arhiva sacuvana: {fajl_arhive} ({len(postojeca_arhiva)} vesti)")
    
    # Azuriraj index
    azuriraj_arhiva_index()


def azuriraj_arhiva_index():
    """Azurira index.json sa listom svih arhiva."""
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


# =====================================================================
# AI OBRADA
# =====================================================================

def napisi_vest(originalni_naslov, originalni_tekst):
    """Vraca dict {naslov, tekst, kategorija} ili None."""
    if not originalni_naslov:
        return None
    
    korisnicki = f"""Napravi novu novinsku vest po pravilima iz sistemskog uputstva.

--- ORIGINALNI NASLOV ---
{originalni_naslov}

--- ORIGINALNI TEKST ---
{originalni_tekst[:3000]}

Vrati iskljucivo JSON sa poljima "naslov", "tekst" i "kategorija":"""
    
    odgovor = pozovi_ai(SISTEM_UPUTSTVO, korisnicki)
    if not odgovor:
        return None
    
    rezultat = parsiraj_json(odgovor)
    if not rezultat or not rezultat.get("naslov") or not rezultat.get("tekst"):
        return None
    
    # Validacija kategorije
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


def pozovi_ai(sistem, korisnik):
    """Poziva aktivni AI model sa retry logikom."""
    for pokusaj in range(3):
        try:
            if USE_OLLAMA:
                r = pozovi_ollama(sistem, korisnik)
            else:
                r = pozovi_gemini(sistem, korisnik)
            
            if r and len(r.strip()) > 30:
                return r
            print(f"  [PRAZAN] Pokusaj {pokusaj+1}/3")
        except Exception as e:
            print(f"  [GRESKA] Pokusaj {pokusaj+1}/3: {e}")
        time.sleep(5)
    return ""


def pozovi_gemini(sistem, korisnik):
    payload = {
        "system_instruction": {"parts": [{"text": sistem}]},
        "contents": [{"parts": [{"text": korisnik}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 2500,
            "responseMimeType": "application/json"
        }
    }
    r = requests.post(GEMINI_URL, json=payload, timeout=90)
    if r.status_code == 200:
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return ""
    print(f"  Gemini status {r.status_code}: {r.text[:200]}")
    return ""


def pozovi_ollama(sistem, korisnik):
    payload = {
        "model": OLLAMA_MODEL,
        "system": sistem,
        "prompt": korisnik,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.85, "num_ctx": 8192, "num_predict": 2500}
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=180)
    if r.status_code == 200:
        return r.json().get("response", "")
    print(f"  Ollama status {r.status_code}")
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

def nadji_sliku(naslov, kategorija, entry=None):
    """Hibridno: original RSS -> Pexels -> Pollinations."""
    if not naslov:
        return ""
    
    ime_fajla = f"slika_{int(time.time()*1000)}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    headers = {"User-Agent": USER_AGENT}
    
    # 1. Original iz RSS-a
    if entry is not None:
        orig_url = uzmi_originalnu_sliku(entry)
        if orig_url:
            if preuzmi_sliku(orig_url, putanja, headers):
                print(f"  [SLIKA] Originalna iz RSS-a")
                return ime_fajla
    
    # 2. Pexels
    if PEXELS_API_KEY:
        keywords = napravi_kljucne_reci(naslov, kategorija)
        if keywords:
            pexels_url = pretrazi_pexels(keywords)
            if pexels_url:
                if preuzmi_sliku(pexels_url, putanja, headers):
                    print(f"  [SLIKA] Pexels: {keywords}")
                    return ime_fajla
    
    # 3. Pollinations (fallback)
    prompt_fallback = {
        "Politika": "government building, dramatic sky, moody",
        "Hronika": "empty street at night, police lights blur, moody",
        "Sport": "empty stadium, sports field, dramatic lighting",
        "Ekonomija": "industrial buildings, dusk, factory",
        "Društvo": "city street, morning fog, moody atmosphere",
        "Svet": "world map, dramatic clouds, atmosphere",
    }
    prompt = prompt_fallback.get(kategorija, "small town, morning fog")
    finalni = f"{prompt}, no people, no faces, cinematic, landscape, 4k"
    encoded = requests.utils.quote(finalni)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=500&nologo=true&seed={int(time.time())}"
    if preuzmi_sliku(url, putanja, headers, timeout=120):
        print(f"  [SLIKA] Pollinations")
        return ime_fajla
    
    return ""


def preuzmi_sliku(url, putanja, headers, timeout=30):
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            with open(putanja, "wb") as f:
                f.write(r.content)
            return True
    except Exception as e:
        print(f"  Slika greska: {e}")
    return False


def napravi_kljucne_reci(naslov, kategorija):
    """Gemini pravi 2-3 engleske kljucne reci za Pexels."""
    prompt = f"""Convert this Serbian news headline into 2-3 ENGLISH keywords for stock photo search.
Focus on VISUAL elements (objects, places, atmosphere). NOT people.
Category: {kategorija}
Headline: {naslov}
Return ONLY keywords separated by space, nothing else.
Example: "power lines sunset" or "basketball court" or "city hall building"."""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 30}
    }
    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=30)
        if r.status_code == 200:
            res = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return res.replace('"', '').replace("\n", " ").strip()[:80]
    except Exception:
        pass
    return ""


def pretrazi_pexels(keywords):
    if not PEXELS_API_KEY:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": keywords, "per_page": 3, "orientation": "landscape"},
            timeout=30
        )
        if r.status_code == 200:
            photos = r.json().get("photos", [])
            if photos:
                return photos[0]["src"].get("large") or photos[0]["src"].get("medium")
    except Exception as e:
        print(f"  Pexels greska: {e}")
    return None


def uzmi_originalnu_sliku(entry):
    for attr in ('media_content', 'media_thumbnail'):
        if hasattr(entry, attr):
            for m in getattr(entry, attr) or []:
                if m.get('url'):
                    return m['url']
    if hasattr(entry, 'enclosures'):
        for e in entry.enclosures or []:
            if 'image' in e.get('type', ''):
                return e.get('href')
    sadrzaj = entry.get('summary', '') + entry.get('description', '')
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', sadrzaj)
    if match:
        return match.group(1)
    return None


if __name__ == "__main__":
    prikupi_vesti()