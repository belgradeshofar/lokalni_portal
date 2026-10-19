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

# NOVI MODEL
AI_MODEL = "gemini-3.8-flash"

FREENEWS_HOSTS = ["www.kurir.rs", "www.novosti.rs", "www.alo.rs", "n1info.rs"]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
ARHIVA_FOLDER = os.path.join(OUTPUT_FOLDER, "arhiva")
ARHIVA_INDEX = os.path.join(ARHIVA_FOLDER, "index.json")

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


def prikupi_vesti():
    print(f"--- START ---")
    print(f"AI: Gemini ({AI_MODEL})")
    print(f"Gemini key: {'DA' if GEMINI_API_KEY else 'NE'}")

    if not GEMINI_API_KEY:
        print("GRESKA: GEMINI_API_KEY nije podesen!")
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
                print("  Preskacem (AI fail)")
                greske += 1
                continue
            if rezultat.get("preskoci"):
                print(f"  Preskacem (nije dnevna vest)")
                odbijeno += 1
                continue

            naslov_lower = rezultat["naslov"].lower()
            tekst_lower = rezultat["tekst"][:500].lower()
            if any(rec in naslov_lower or rec in tekst_lower for rec in HRONIKA_KLJUCNE):
                if rezultat["kategorija"] != "Hronika":
                    print(f"  [KOREKCIJA] {rezultat['kategorija']} -> Hronika")
                    rezultat["kategorija"] = "Hronika"

            # Trazimo sliku i proveravamo je preko Vision AI
            slika_url = ""
            for pokusaj in range(3):
                potencijalna = pronadji_sliku(rezultat["naslov"], rezultat["kategorija"])
                
                if potencijalna and potencijalna not in koriscene_slike:
                    if proveri_sliku_vision(potencijalna, rezultat["naslov"]):
                        slika_url = potencijalna
                        koriscene_slike.add(potencijalna)
                        print(f"  [SLIKA] Prihvaćena: {slika_url[:70]}")
                        break
                    else:
                        print(f"  [SLIKA] Odbijena od strane AI-ja (ljudi/pogrešan kontekst)")
                time.sleep(1)

            if not slika_url:
                print(f"  Slika nije pronadjena nakon 3 pokusaja.")

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
            time.sleep(1.5)
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


def proveri_sliku_vision(slika_url, naslov):
    """Koristi Gemini 3.8 Flash da vidi da li je slika prikladna za vest."""
    try:
        r = requests.get(slika_url, timeout=15)
        if r.status_code != 200:
            return False
        
        prompt = f"""Pogledaj ovu sliku. Da li je prikladna za ozbiljnu novinsku vest pod naslovom: "{naslov}"?
PRAVILA:
1. Ako na slici ima ljudi, lica, nasmejanih ljudi, modela ili grupa ljudi -> ODGOVORI SA "NE".
2. Ako je slika potpuno apstraktna, pejzaž, zgrada, ulica, objekat -> ODGOVORI SA "DA".
3. Ako slika prikazuje nešto što očigledno nije iz Evrope/Srbije (npr. pustinja, džungla, azijski grad) -> ODGOVORI SA "NE".

Odgovori ISKLJUČIVO sa jednom rečju: DA ili NE."""

        response = client.models.generate_content(
            model=AI_MODEL,
            contents=[
                types.Part.from_bytes(data=r.content, mime_type="image/jpeg"),
                prompt
            ],
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=5)
        )
        
        odgovor = response.text.strip().upper()
        return "DA" in odgovor
        
    except Exception as e:
        print(f"    Vision greska: {e}")
        return False


def napisi_vest(originalni_naslov, originalni_tekst):
    if not originalni_naslov:
        return None
        
    korisnicki = f"""Napisi novu dnevnu vest po pravilima.
ZAPAMTI: PRIHVATI u 95% slucajeva.
Gramatika MORA biti ispravna.
Vrati iskljucivo JSON.

--- ORIGINALNI NASLOV ---
{originalni_naslov}

--- ORIGINALNI TEKST ---
{originalni_tekst[:3000]}"""

    try:
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=korisnicki,
            config=types.GenerateContentConfig(
                system_instruction=SISTEM_UPUTSTVO,
                temperature=0.3,
                max_output_tokens=2500,
                response_mime_type="application/json"
            )
        )
        
        odgovor = response.text
        rezultat = json.loads(odgovor)
        
        if rezultat.get("preskoci"):
            return rezultat
            
        if not rezultat.get("naslov") or not rezultat.get("tekst"):
            print("    [DEBUG] Nedostaje naslov ili tekst")
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
        
    except Exception as e:
        print(f"  [GRESKA GEMINI] {e}")
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