import feedparser
import os
import json
import time
import requests
import html
import re

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
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ZABRANJENE_RECI = [
    "face", "portrait", "man", "woman", "person", "people", "child",
    "boy", "girl", "president", "politician", "actor", "singer",
    "human", "male", "female", "guy", "lady", "crowd"
]


def prikupi_vesti():
    print(f"--- START ---")
    sve_vesti = []
    prva_slika = True  # Prva slika ne ceka

    for url in RSS_FEEDS:
        print(f"Povezujem se na: {url}...")
        try:
            feed = feedparser.parse(url)
            if feed.bozo or not feed.entries:
                print(f"  Nema vesti: {url}")
                continue

            for entry in feed.entries[:2]:
                originalni_naslov = html.unescape(entry.title)
                originalni_tekst = html.unescape(entry.get('summary', entry.get('description', '')))

                print(f"  Obradujem: {originalni_naslov[:50]}...")

                novi_naslov = preformulisi_tekst(originalni_naslov, "naslov")
                novi_tekst = preformulisi_tekst(originalni_tekst, "tekst kratke novinske vesti")

                # Pre slike, pauza (osim za prvu)
                if not prva_slika:
                    print(f"    Pauza 20s pre slike (rate limit)...")
                    time.sleep(20)
                prva_slika = False

                ime_slike = generisi_sliku(novi_naslov, entry)

                vest = {
                    "naslov": novi_naslov,
                    "tekst": novi_tekst,
                    "slika": ime_slike,
                    "link": entry.link,
                    "datum": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "izvor": url
                }
                sve_vesti.append(vest)
                time.sleep(3)
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
            try:
                result = data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"    [OK] Gemini vratio {tip} ({len(result)} znakova)")
                return html.unescape(result.strip())
            except (KeyError, IndexError):
                print(f"    [GRESKA] Neocekivan odgovor")
                return tekst
        else:
            print(f"    [GRESKA] Status {response.status_code}")
            return tekst
    except Exception as e:
        print(f"    [GRESKA] {e}")
        return tekst


def ocisti_prompt(prompt):
    prompt_lower = prompt.lower()
    for rec in ZABRANJENE_RECI:
        if re.search(r'\b' + re.escape(rec) + r'\b', prompt_lower):
            return None
    return prompt


def uzmi_originalnu_sliku(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        for m in entry.media_content:
            if m.get('url'):
                return m['url']
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for m in entry.media_thumbnail:
            if m.get('url'):
                return m['url']
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for e in entry.enclosures:
            if 'image' in e.get('type', ''):
                return e.get('href')
    sadrzaj = entry.get('summary', '') + entry.get('description', '')
    if sadrzaj:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', sadrzaj)
        if match:
            return match.group(1)
    return None


def generisi_sliku(naslov, entry=None):
    if not naslov:
        return ""

    ime_fajla = f"slika_{int(time.time()*1000)}.jpg"
    putanja = os.path.join(SLIKE_FOLDER, ime_fajla)
    headers = {"User-Agent": USER_AGENT}

    # POKUSAJ 1: Originalna slika iz RSS-a
    if entry is not None:
        original_url = uzmi_originalnu_sliku(entry)
        if original_url:
            try:
                r = requests.get(original_url, headers=headers, timeout=30)
                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    with open(putanja, "wb") as f:
                        f.write(r.content)
                    print(f"    [OK] Originalna slika: {ime_fajla}")
                    return ime_fajla
            except Exception as e:
                print(f"    Nema originalne slike: {e}")

    # POKUSAJ 2: Gemini prompt
    prompt_za_gemini = f"""You are creating a symbolic, ATMOSPHERIC image prompt for a news article.
Headline (in Serbian): {naslov}

Write a SHORT English image prompt (max 12 words) that is PURELY SYMBOLIC and ABSTRACT.
STRICT RULES:
- ABSOLUTELY NO people, no faces, no portraits, no crowds, no silhouettes of humans.
- Focus ONLY on: objects, landscapes, buildings, weather, machines, tools, plants, abstract shapes, textures.
- Use atmospheric words like: moody, dramatic sky, morning fog, empty street, industrial, rustic.
- NO fictional characters, NO realistic faces.

Return ONLY the English prompt, nothing else."""

    engleski_prompt = None
    try:
        g_payload = {
            "contents": [{"parts": [{"text": prompt_za_gemini}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 60}
        }
        g_response = requests.post(GEMINI_URL, json=g_payload, timeout=30)
        if g_response.status_code == 200:
            engleski_prompt = g_response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            engleski_prompt = engleski_prompt.replace("\n", " ").replace('"', '').strip()[:180]
            print(f"    [OK] Prompt: {engleski_prompt}")
    except Exception as e:
        print(f"    [GRESKA] Gemini: {e}")

    if engleski_prompt:
        if ocisti_prompt(engleski_prompt) is None:
            print(f"    Prompt sadrzi zabranjene reci, fallback.")
            engleski_prompt = None

    if not engleski_prompt:
        engleski_prompt = "empty street, morning fog, moody sky, atmospheric"

    finalni_prompt = f"{engleski_prompt}, no people, no faces, cinematic, atmospheric, landscape, 4k"

    # POKUSAJ 3: Pollinations sa retry
    encoded = requests.utils.quote(finalni_prompt)
    max_pokusaja = 3
    for pokusaj in range(max_pokusaja):
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=500&nologo=true&seed={int(time.time()) + pokusaj}"
        try:
            print(f"    Generisem sliku (pokusaj {pokusaj+1}/{max_pokusaja})...")
            response = requests.get(url, headers=headers, timeout=120)
            content_type = response.headers.get("content-type", "")
            if response.status_code == 200 and "image" in content_type:
                with open(putanja, "wb") as f:
                    f.write(response.content)
                print(f"    [OK] Slika: {ime_fajla}")
                return ime_fajla
            elif response.status_code == 402:
                print(f"    [402] Rate limit, cekam 30s...")
                time.sleep(30)
            else:
                print(f"    [GRESKA] Status {response.status_code}, tip {content_type}")
                time.sleep(10)
        except Exception as e:
            print(f"    [GRESKA] {e}")
            time.sleep(10)

    print(f"    Slika nije generisana posle {max_pokusaja} pokusaja")
    return ""


if __name__ == "__main__":
    prikupi_vesti()