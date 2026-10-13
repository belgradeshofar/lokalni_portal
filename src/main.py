import feedparser
import os
import json
import time
import requests

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

def prikupi_vesti():
    sve_vesti = []
    
    for url in RSS_FEEDS:
        print(f"Povezujem se na: {url}...")
        try:
            feed = feedparser.parse(url)
            if feed.bozo or not feed.entries:
                print(f"  ⚠️ Nema vesti ili greška: {url}")
                continue

            for entry in feed.entries[:2]:  # Uzimamo prve 2 vesti po portalu za test
                originalni_naslov = entry.title
                originalni_tekst = entry.get('summary', entry.get('description', ''))

                print(f"  🤖 Obrađujem: {originalni_naslov[:40]}...")

                # 1. Preformulisanje naslova i teksta
                novi_naslov = preformulisi_tekst(originalni_naslov, "naslov")
                novi_tekst = preformulisi_tekst(originalni_tekst, "tekst")

                # 2. Generisanje slike
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
                time.sleep(2) # Pauza da ne preopteretimo besplatan API

        except Exception as e:
            print(f"  ❌ Greška: {e}")
            continue

    # Čuvanje rezultata
    os.makedirs(SLIKE_FOLDER, exist_ok=True)
    
    with open(VESTI_FAJL, "w", encoding="utf-8") as f:
        json.dump(sve_vesti, f, ensure_ascii=False, indent=4)
    
    print(f"\n📦 Ukupno sačuvano {len(sve_vesti)} vesti u {VESTI_FAJL}")

def preformulisi_tekst(tekst, tip):
    """Koristi Pollinations.AI za preformulisanje teksta."""
    if not tekst:
        return ""
    
    prompt = (
        f"Ti si iskusni novinar lokalnih vesti u Srbiji. "
        f"Preformuliši sledeći {tip} na srpskom jeziku, u profesionalnom novinarskom stilu, "
        f"zadržavajući sve činjenice. Vrati samo preformulisani tekst.\n\n"
        f"Original: {tekst}"
    )
    
    try:
        # Besplatan Pollinations text API
        encoded_prompt = requests.utils.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return tekst
    except Exception as e:
        print(f"    ⚠️ Greška pri preformulisanju: {e}")
        return tekst

def generisi_sliku(naslov):
    """Generiše sliku na osnovu naslova vesti."""
    if not naslov:
        return ""
    
    ime_fajla = f"slika_{int(time.time())}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    
    prompt = f"Novinska fotografija: {naslov}, realistično, profesionalno"
    
    try:
        # Besplatan Pollinations image API
        encoded_prompt = requests.utils.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=500&nologo=true"
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            with open(putanja, "wb") as f:
                f.write(response.content)
            return ime_fajla
        else:
            return ""
    except Exception as e:
        print(f"    ⚠️ Greška pri generisanju slike: {e}")
        return ""

if __name__ == "__main__":
    prikupi_vesti()