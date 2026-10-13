import feedparser
import os
import json
import time
import requests

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
                print(f"  Nema vesti ili greska: {url}")
                continue

            for entry in feed.entries[:2]:
                originalni_naslov = entry.title
                originalni_tekst = entry.get('summary', entry.get('description', ''))
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
                time.sleep(2)
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
    prompt = f"Ti si iskusni novinar lokalnih vesti u Srbiji. Preformuliši sledeći {tip} na srpskom jeziku, u profesionalnom novinarskom stilu, zadržavajući sve činjenice. Vrati samo preformulisani tekst.\n\nOriginal: {tekst}"
    try:
        encoded_prompt = requests.utils.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            print(f"    AI je vratio preformulisan {tip}.")
            return response.text.strip()
        else:
            print(f"    AI greska: {response.status_code}")
            return tekst
    except Exception as e:
        print(f"    Greska pri preformulisanju: {e}")
        return tekst

def generisi_sliku(naslov):
    if not naslov:
        return ""
    ime_fajla = f"slika_{int(time.time())}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    prompt = f"Novinska fotografija: {naslov}, realistično, profesionalno"
    try:
        encoded_prompt = requests.utils.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=500&nologo=true"
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            with open(putanja, "wb") as f:
                f.write(response.content)
            print(f"    Slika generisana: {ime_fajla}")
            return ime_fajla
        else:
            print(f"    Greska pri generisanju slike: {response.status_code}")
            return ""
    except Exception as e:
        print(f"    Greska pri generisanju slike: {e}")
        return ""

if __name__ == "__main__":
    prikupi_vesti()