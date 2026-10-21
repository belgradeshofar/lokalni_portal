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
from google import genai
from google.genai import types
from image_finder import pronadji_sliku, reset_rotacije

# =====================================================================
# KONFIGURACIJA
# =====================================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

AI_MODEL = "gemini-3.1-flash-lite"

FREENEWS_HOSTS = ["www.kurir.rs", "www.novosti.rs", "www.alo.rs", "n1info.rs"]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
ARHIVA_FOLDER = os.path.join(OUTPUT_FOLDER, "arhiva")
ARHIVA_INDEX = os.path.join(ARHIVA_FOLDER, "index.json")

# Putanje za lokalnu bazu slika
BAZA_SLIKA_FOLDER = os.path.join(OUTPUT_FOLDER, "baza_slika")
USED_IMAGES_FILE = os.path.join(OUTPUT_FOLDER, "used_images.json")

MAX_VESTI_U_GLAVNOM = 200
MAX_NOVIH_PO_POKRETANJU = 30
VESTI_PO_IZVORU = 8

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KATEGORIJE = ["Hronika", "Društvo", "Ekonomija", "Sport"]

PRETRAGE = {
    "Hronika": ["hapšenje uhapšen priveden", "sud tužilaštvo presuda", "saobraćajna nesreća poginuo", "požar eksplozija", "ubistvo napad", "krađa razbojništvo", "policija istraga droga", "sudjenje optužnica pritvor"],
    "Društvo": ["vlada ministarstvo", "opština grad skupština", "izbori protest", "zdravstvo obrazovanje škola", "poplava sneg oluja vreme", "studenti fakultet"],
    "Ekonomija": ["cena dinara evra", "inflacija plata penzija", "budžet investicija", "fabrika kompanija privreda", "poljoprivreda turizam sajam"],
    "Sport": ["crvena zvezda partizan", "reprezentacija utakmica", "derbi fudbal košarka"],
}

GOOGLE_NEWS_QUERIES = [
    ("hronika", "Hronika"), ("saobraćajna nesreća", "Hronika"), ("požar", "Hronika"),
    ("hapšenje", "Hronika"), ("sud presuda", "Hronika"), ("ubistvo", "Hronika"),
    ("krađa", "Hronika"), ("droga zaplena", "Hronika"), ("društvo Srbija", "Društvo"),
    ("ekonomija Srbija", "Ekonomija"), ("sport Srbija", "Sport"),
]

HRONIKA_KLJUCNE = [
    "uhapšen", "uhapsen", "hapšenje", "hapsenje", "priveden", "pritvor", "sud", "tužilaštvo", "tuzilastvo", 
    "presuda", "optužnica", "optuznica", "nesreća", "nesreca", "saobraćajna", "saobracajna", "poginuo", 
    "povređen", "povredjen", "požar", "pozar", "eksplozija", "ubistvo", "ubica", "napad", "krađa", "kradja",
    "razbojništvo", "razbojnistvo", "policija", "mup", "istraga", "droga", "narkotik", "zaplena", "kriminal"
]

SISTEM_UPUTSTVO = """Ti si iskusni novinar i urednik informativnog portala u Srbiji.
Tvoj zadatak: od sirovih informacija sa drugih portala napisati NOVU, originalnu, profesionalnu DNEVNU VEST.

=== NAJVAZNIJE PRAVILO ===
PRIHVATI vest u 95% slucajeva. Odbij SAMO jasnu analizu, kolumnu, intervju ili showbiz.

=== KATEGORIZACIJA ===
Ako naslov ili tekst sadrži reci: uhapšen, sud, nesreća, požar, ubistvo, policija, krađa -> kategorija MORA biti HRONIKA.
Ako nije Hronika, onda: DRUSTVO (vlada, izbori, škola), EKONOMIJA (cene, penzije), SPORT (utakmice).

=== GRAMATIKA SRPSKOG JEZIKA ===
Tvoj tekst MORA biti GRAMATICKI ISPRAVAN. Ne izmisljaj reci.
Padezi: "protiv dva lekara", "u Novom Sadu", "kod Beograda", "iz Niša".
Ako nisi siguran kako se rec pise, koristi drugu rec koju sigurno znas.

=== PREFORMULISANJE ===
NE KOPIRAJ originalne recenice. Napisi SVOJIM RECIMA.
Promeni red reci, koristi sinonime (uhapsiti->privesti), promeni strukturu.
Zadrzi SVE cinjenice: imena, datume, brojeve, mesta.

=== FORMAT ODGOVORA ===
Vrati ISKLJUČIVO JSON:
{
  "preskoci": false,
  "naslov": "Tvoj novi naslov",
  "tekst": "Tvoj novi tekst u 3-5 pasusa...",
  "kategorija": "Hronika" 
}
Ako odbijas vest, vrati: {"preskoci": true}
"""

# =====================================================================
# LOGIKA ZA LOKALNE SLIKE
# =====================================================================

def ucitaj_iskoriscene_slike():
    if not os.path.exists(USED_IMAGES_FILE):
        return {}
    try:
        with open(USED_IMAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def sacuvaj_iskoriscene_slike(iskoriscene):
    with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(iskoriscene, f, ensure_ascii=False, indent=2)

def uzmi_lokalnu_sliku(kategorija):
    """Bira sliku iz lokalnog foldera, rotira ih i pamti šta je iskoristio."""
    # Mapiranje kategorija na foldere
    mapiranje = {
        "Hronika": "hronika",
        "Politika": "politika",
        "Sport": ["fudbal", "kosarka"], # Sport će naizmenično uzimati iz oba
    }
    
    if kategorija not in mapiranje:
        return None # Nema lokalnu sliku za ovu kategoriju (Društvo, Ekonomija)

    folder_imena = mapiranje[kategorija]
    
    # Ako je lista (za Sport), uzmi nasumično jedan od ponuđenih foldera
    if isinstance(folder_imena, list):
        folder_imena = random.choice(folder_imena)

    folder_path = os.path.join(BAZA_SLIKA_FOLDER, folder_imena)
    
    if not os.path.exists(folder_path):
        return None

    sve_slike = [f for f in os.listdir(folder_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
    if not sve_slike:
        return None

    iskoriscene = ucitaj_iskoriscene_slike()
    if folder_imena not in iskoriscene:
        iskoriscene[folder_imena] = []

    dostupne = [s for s in sve_slike if s not in iskoriscene[folder_imena]]

    # Ako su sve iskorišćene, resetujemo listu za taj folder
    if not dostupne:
        iskoriscene[folder_imena] = []
        dostupne = sve_slike

    izabrana = random.choice(dostupne)
    iskoriscene[folder_imena].append(izabrana)
    sacuvaj_iskoriscene_slike(iskoriscene)

    # Vraćamo relativnu putanju za sajt
    return f"content/baza_slika/{folder_imena}/{izabrana}"

# =====================================================================
# GENERISANJE SLIKE (Krajnji fallback)
# =====================================================================

def generisi_sliku_pollinations(naslov, kategorija):
    prompt_baza = {
        "Hronika": "empty street night fog",
        "Društvo": "city street morning fog",
        "Ekonomija": "industrial factory dusk",
        "Sport": "empty stadium floodlights",
    }
    baza = prompt_baza.get(kategorija, "european city morning")
    finalni = f"{baza}, no people, cinematic, photorealistic"
    encoded = urllib.parse.quote(finalni)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=500&nologo=true"
    
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            ime_fajla = f"slika_{int(time.time())}.jpg"
            putanja = os.path.join(OUTPUT_FOLDER, "slike", ime_fajla)
            os.makedirs(os.path.dirname(putanja), exist_ok=True)
            with open(putanja, "wb") as f:
                f.write(r.content)
            return f"content/slike/{ime_fajla}"
    except Exception as e:
        print(f"    Greska pri generisanju: {e}")
    return ""

# =====================================================================
# GLAVNA FUNKCIJA
# =====================================================================

def prikupi_vesti():
    print(f"--- START ---")
    print(f"AI: Gemini ({AI_MODEL})")
    print(f"Gemini key: {'DA' if GEMINI_API_KEY else 'NE'}")

    if not GEMINI_API_KEY:
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(ARHIVA_FOLDER, exist_ok=True)

    reset_rotacije()
    postojece = ucitaj_postojece()
    print(f"Postojecih vesti: {len(postojece)}")
    postojeci_linkovi = {v.get("link") for v in postojece}

    kandidati = []
    seen_links = set()

    for host in FREENEWS_HOSTS:
        for kategorija, pretrage in PRETRAGE.items():
            for pretraga in pretrage:
                try:
                    params = {"host": host, "q": pretraga, "date": "24h", "size": VESTI_PO_IZVORU, "sort": "date", "fields": "title,url,published_at,description,image"}
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
                except Exception:
                    pass
                time.sleep(0.2)

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
        except Exception:
            pass
        time.sleep(0.2)

    hronika_kand = [k for k in kandidati if k["kategorija"] == "Hronika"]
    ostali_kand = [k for k in kandidati if k["kategorija"] != "Hronika"]
    random.shuffle(hronika_kand)
    random.shuffle(ostali_kand)

    max_hronika = int(MAX_NOVIH_PO_POKRETANJU * 0.6)
    kandidati = hronika_kand[:max_hronika] + ostali_kand[:MAX_NOVIH_PO_POKRETANJU - max_hronika]
    random.shuffle(kandidati)

    print(f"Ukupno kandidata: {len(kandidati)} (Hronika: {len(hronika_kand)})")

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
                greske += 1
                continue
            if rezultat.get("preskoci"):
                odbijeno += 1
                continue

            naslov_lower = rezultat["naslov"].lower()
            tekst_lower = rezultat["tekst"][:500].lower()
            if any(rec in naslov_lower or rec in tekst_lower for rec in HRONIKA_KLJUCNE):
                if rezultat["kategorija"] != "Hronika":
                    rezultat["kategorija"] = "Hronika"

            # --- SLIKA LOGIKA ---
            slika_url = ""
            
            # 1. Probaj lokalnu bazu
            slika_url = uzmi_lokalnu_sliku(rezultat["kategorija"])
            if slika_url:
                print(f"  [SLIKA] Lokalna baza: {slika_url}")

            # 2. Ako nema lokalne, probaj internet
            if not slika_url:
                keywords_en = napravi_kljucne_reci(rezultat["naslov"], rezultat["kategorija"])
                slika_url = pronadji_sliku(rezultat["naslov"], rezultat["kategorija"], keywords_en)
                if slika_url:
                    print(f"  [SLIKA] Internet: {slika_url[:70]}")

            # 3. Ako i to ne uspe, generiši
            if not slika_url:
                slika_url = generisi_sliku_pollinations(rezultat["naslov"], rezultat["kategorija"])
                if slika_url:
                    print(f"  [SLIKA] Generisana: {slika_url}")

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
            print(f"  [SAVED] Sacuvano {len(sve_vesti)} vesti")
            time.sleep(2)
        except Exception as e:
            print(f"  Greska: {e}")
            greske += 1
            continue

    sve_vesti.sort(key=lambda x: x.get("datum", ""), reverse=True)
    sve_vesti = sve_vesti[:MAX_VESTI_U_GLAVNOM]
    sacuvaj_trenutno(sve_vesti)
    sacuvaj_arhivu(sve_vesti)

    print(f"\n--- KRAJ ---")
    print(f"Prihvaceno: {prihvaceno}, Odbijeno: {odbijeno}, Greske: {greske}")

# (Ostatak funkcija: napisi_vest, napravi_kljucne_reci, ocisti_tekst, sacuvaj_trenutno, ucitaj_postojece, sacuvaj_arhivu, azuriraj_arhiva_index ostaju isti kao u prethodnom kodu)
# ... [Ovde bi isle te funkcije, ali sam ih skratio da bi poruka bila citljivija. One su vec u tvom kodu.] ...