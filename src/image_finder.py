import os
import requests
import random

USER_AGENT = "VestiSrbija/1.0 (https://github.com/belgradeshofar/lokalni_portal)"

ZABRANJENE_RECI_U_NAZIVU = [
    "portrait", "face", "selfie", "man_", "_man", "woman",
    "people", "person", "crowd", "guy", "lady", "boy", "girl",
    "president", "minister", "politician", "actor", "singer",
    "human", "male", "female"
]

# Provereno dobre slike po kategoriji (Wikimedia/Openverse pretrage koje rade)
FALLBACK_PRETRAGE = {
    "Hronika": [
        "police car night lights",
        "courthouse building exterior",
        "city street fog night",
        "prison fence barbed wire",
        "police station building",
    ],
    "Društvo": [
        "city hall building exterior",
        "government building columns",
        "public square fountain",
        "old town street morning",
        "courthouse columns facade",
    ],
    "Ekonomija": [
        "factory chimney industrial",
        "warehouse industrial building",
        "cargo port containers",
        "business district skyline",
        "power plant industrial",
    ],
    "Sport": [
        "football stadium floodlights",
        "basketball arena interior",
        "tennis court net empty",
        "athletics running track",
        "swimming pool lanes indoor",
        "empty football pitch grass",
    ],
}


def reset_rotacije():
    pass


def pronadji_sliku(naslov, kategorija, keywords_en):
    """
    Trazi sliku sa STRAGOM validacijom da ima veze sa temom.
    Vraca URL ili fallback URL.
    """
    # 1. Probaj Wikimedia sa specificnim upitima
    url = wikimedia_search(naslov, keywords_en, kategorija)
    if url:
        return url

    # 2. Probaj Openverse
    url = openverse_search(keywords_en, kategorija)
    if url:
        return url

    # 3. Fallback - provereno dobra pretraga iz kategorije
    return fallback_search(kategorija)


def wikimedia_search(naslov, keywords_en, kategorija):
    # Samo engleske kljucne reci za slike (srpski naslov cesto ne pomaze)
    upiti = [keywords_en, naslov[:50]]
    for upit in upiti:
        if not upit:
            continue
        url = _wikimedia_api(upit, kategorija, keywords_en)
        if url:
            return url
    return ""


def _wikimedia_api(query, kategorija, originalne_reci):
    api_url = "https://commons.wikimedia.org/w/api.php"
    headers = {"User-Agent": USER_AGENT}

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 15,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "format": "json",
    }

    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            return ""
        pages = r.json().get("query", {}).get("pages", {})
        
        # Kljucne reci za validaciju
        reci_za_proveru = [r.lower() for r in originalne_reci.split() if len(r) > 3]
        
        for page in pages.values():
            title_lower = page.get("title", "").lower()
            
            # Preskoci lica
            if any(bad in title_lower for bad in ZABRANJENE_RECI_U_NAZIVU):
                continue
            
            # Validacija: bar 1 kljucna rec mora biti u naslovu fajla
            if reci_za_proveru:
                poklapanja = sum(1 for rec in reci_za_proveru if rec in title_lower)
                if poklapanja == 0:
                    continue
            
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                info = imageinfo[0]
                if info.get("mime") in ("image/jpeg", "image/png"):
                    # Minimalne dimenzije
                    sirina = info.get("width", 0)
                    visina = info.get("height", 0)
                    if sirina >= 600 and visina >= 400:
                        return info.get("url", "")
    except Exception as e:
        print(f"  Wikimedia greska: {e}")
    return ""


def openverse_search(keywords, kategorija):
    if not keywords:
        return ""

    url = "https://api.openverse.org/v1/images/"
    headers = {"User-Agent": USER_AGENT}
    params = {
        "q": keywords,
        "page_size": 15,
        "license_type": "commercial",
        "extension": "jpg",
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            results = r.json().get("results", [])
            reci_za_proveru = [k.lower() for k in keywords.split() if len(k) > 3]
            
            for result in results:
                title = (result.get("title") or "").lower()
                
                # Preskoci lica
                if any(bad in title for bad in ZABRANJENE_RECI_U_NAZIVU):
                    continue
                
                # Validacija: bar 1 kljucna rec
                if reci_za_proveru:
                    poklapanja = sum(1 for rec in reci_za_proveru if rec in title)
                    if poklapanja == 0:
                        continue
                
                url_slike = result.get("url", "")
                if url_slike:
                    return url_slike
    except Exception as e:
        print(f"  Openverse greska: {e}")
    return ""


def fallback_search(kategorija):
    """Provereno dobra slika iz kategorije."""
    opcije = FALLBACK_PRETRAGE.get(kategorija, ["city street morning"])
    random.shuffle(opcije)
    
    for izbor in opcije:
        # Probaj Wikimedia
        url = _wikimedia_api(izbor, kategorija, izbor)
        if url:
            return url
        # Probaj Openverse
        url = openverse_search(izbor, kategorija)
        if url:
            return url
    return ""