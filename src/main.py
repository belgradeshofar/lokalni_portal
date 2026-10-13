import feedparser
import os
import json
import time
import requests
import html
import base64

# --- KONFIGURACIJA ---
RSS_FEEDS = [
    "https://poportal.rs/feed/",
    "https://rtvbiser.rs/feed/",
    "https://www.ebranicevo.com/feed/",
    "https://www.ekucevo.rs/feed/",
    "https://rtvkucevo.com/feed/",
    "https://smederevouzivo.rs/feed/",
    "https://palankainfo.com/feed/",
    "https://sumadijskevesti.com/feed/",
    "https://urbancityradio.org/feed/",
    "https://www.k1info.rs/feed/",
]

OUTPUT_FOLDER = "content"
VESTI_FAJL = os.path.join(OUTPUT_FOLDER, "vesti.json")
SLIKE_FOLDER = os.path.join(OUTPUT_FOLDER, "slike")

# Token se cita iz GitHub Secrets, ne stoji u kodu
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def prikupi_vesti():
    sve_vesti = []
    for url in RSS_FEEDS:
        print(f"Povezujem se na: {url}...")
        try:
            feed = feedparser.parse(url)
            if feed.bozo or not feed.entries:
                print(f"  Nema vesti ili greska: {url}")
                continue

            for entry in feed.entries[:2]:  # Prve 2 po portalu za test
                originalni_naslov = html.unescape(entry.title)
                originalni_tekst = html.unescape(entry.get('summary', entry.get('description', '')))
                print(f"  Obradujem: {originalni_naslov[:40]}...")

                novi_naslov = preformulisi_tekst(originalni_naslov, "naslov")
                novi_tekst = preformulisi_tekst(originalni_tekst, "tekst")
                ime_slike = generisi_sliku(novi_naslov)

                vest = {
                    "naslov": novi_naslov,
                    "tekst": novi_tekst,
                    "slika": ime_slike,
                    "link": entry.link,
                    "datum": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "izvor": url
                }
                sve_vesti.append(vest)
                time.sleep(1)

        except Exception as e:
            print(f"  Greska: {e}")
            continue

    os.makedirs(SLIKE_FOLDER, exist_ok=True)
    with open(VESTI_FAJL, "w", encoding="utf-8") as f:
        json.dump(sve_vesti, f, ensure_ascii=False, indent=4)
    print(f"\nUkupno sacuvano {len(sve_vesti)} vesti u {VESTI_FAJL}")

def preformulisi_tekst(tekst, tip):
    if not tekst:
        return ""
    
    # Koristimo model koji dobro radi na srpskom i dostupan je besplatno
    model_url = "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct"
    
    prompt = f"Ti si iskusni novinar lokalnih vesti u Srbiji. Preformuliši sledeći {tip} na srpskom jeziku, u profesionalnom novinarskom stilu, zadržavajući sve činjenice. Vrati samo preformulisani tekst.\n\nOriginal: {tekst}"
    
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 500, "temperature": 0.7, "return_full_text": False}
    }
    
    try:
        response = requests.post(model_url, headers=HF_HEADERS, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return html.unescape(result[0].get('generated_text', tekst).strip())
            return tekst
        else:
            print(f"    AI greska (tekst): Status {response.status_code} - {response.text[:100]}")
            return tekst
    except Exception as e:
        print(f"    Greska pri preformulisanju: {e}")
        return tekst

def generisi_sliku(naslov):
    if not naslov:
        return ""
    
    ime_fajla = f"slika_{int(time.time())}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    
    model_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    prompt = f"News photograph: {naslov}, realistic, professional, 4k"
    
    try:
        print(f"    Generisem sliku...")
        response = requests.post(model_url, headers=HF_HEADERS, json={"inputs": prompt}, timeout=90)
        if response.status_code == 200:
            with open(putanja, "wb") as f:
                f.write(response.content)
            print(f"    Slika generisana: {ime_fajla}")
            return ime_fajla
        else:
            print(f"    Greska pri generisanju slike: Status {response.status_code}")
            return ""
    except Exception as e:
        print(f"    Greska pri generisanju slike: {e}")
        return ""

if __name__ == "__main__":
    prikupi_vesti()