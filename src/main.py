import feedparser
import os
import json
import time
import requests
import html

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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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
                originalni_naslov = html.unescape(entry.title)
                originalni_tekst = html.unescape(entry.get('summary', entry.get('description', '')))
                
                print(f"  Obradujem: {originalni_naslov[:50]}...")

                novi_naslov = preformulisi_tekst(originalni_naslov, "naslov")
                novi_tekst = preformulisi_tekst(originalni_tekst, "tekst kratke novinske vesti")
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
    print(f"\nUkupno sacuvano {len(sve_vesti)} vesti.")

def preformulisi_tekst(tekst, tip):
    if not tekst:
        return ""
    
    prompt = f"""Ti si iskusni novinar lokalnih vesti u Srbiji. 
Preformuliši sledeći {tip} na srpskom jeziku, u profesionalnom novinarskom stilu. 
PRAVILA:
- Zadrži sve činjenice, imena, datume i brojeve.
- Promeni strukturu rečenica (nemoj samo zameniti po neku reč).
- Ukloni HTML tagove, linkove i fraze poput "The post... appeared first on...".
- Vrati SAMO preformulisani tekst, bez uvoda i objašnjenja.

Original:
{tekst}"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 800}
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            result = data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"    Gemini je vratio preformulisan {tip}.")
            return html.unescape(result.strip())
        else:
            print(f"    Gemini greska: {response.status_code} - {response.text[:200]}")
            return tekst
    except Exception as e:
        print(f"    Greska pri preformulisanju: {e}")
        return tekst

def generisi_sliku(naslov):
    if not naslov:
        return ""
    
    ime_fajla = f"slika_{int(time.time()*1000)}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    
    prompt = f"news photograph, {naslov}, realistic, professional press photo"
    encoded = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=500&nologo=true&seed={int(time.time())}"
    headers = {"User-Agent": USER_AGENT}
    
    try:
        print(f"    Generisem sliku...")
        response = requests.get(url, headers=headers, timeout=120)
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200 and "image" in content_type:
            with open(putanja, "wb") as f:
                f.write(response.content)
            print(f"    Slika generisana: {ime_fajla}")
            return ime_fajla
        else:
            print(f"    Greska slike: Status {response.status_code}, tip {content_type}")
            return ""
    except Exception as e:
        print(f"    Greska pri generisanju slike: {e}")
        return ""

if __name__ == "__main__":
    prikupi_vesti()