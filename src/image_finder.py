import os
import requests
import random

USER_AGENT = "VestiSrbija/1.0 (https://github.com/belgradeshofar/lokalni_portal)"

ZABRANJENE_RECI_U_NAZIVU = [
    "portrait", "face", "selfie", "man_", "_man", "woman",
    "people", "person", "crowd", "guy", "lady", "boy", "girl",
    "president", "minister", "politician", "actor", "singer",
    "human", "male", "female", "smile", "happy", "laugh"
]

# Strogo definisane pretrage - bez ljudi, apstraktno, evropski kontekst
SIGURNE_PRETRAGE = {
    "Hronika": [
        "police car night lights", "courthouse building exterior", "city street fog night", 
        "prison fence barbed wire", "empty street dusk", "police lights reflection"
    ],
    "Društvo": [
        "city hall building exterior", "government building columns", "public square fountain", 
        "old town street morning", "courthouse columns facade", "european city architecture"
    ],
    "Ekonomija": [
        "factory chimney industrial", "warehouse industrial building", "cargo port containers", 
        "business district skyline", "power plant industrial", "empty office building"
    ],
    "Sport": [
        "football stadium floodlights", "basketball arena interior", "tennis court net empty", 
        "athletics running track", "swimming pool lanes indoor", "empty football pitch grass"
    ],
}

def reset_rotacije():
    pass

def pronadji_sliku(naslov, kategorija, keywords_en=""):
    """
    Trazi sliku koristeci STROGO bezbedne pretrage.
    Ignorise keywords_en kako bi se izbegle cudne pretrage.
    """
    opcije = SIGURNE_PRETRAGE.get(kategorija, ["european city street morning"])
    random.shuffle(opcije)
    
    for upit in opcije:
        # 1. Probaj Wikimedia
        url = _wikimedia_api(upit)
        if url:
            return url
            
        # 2. Probaj Openverse
        url = _openverse_api(upit)
        if url:
            return url
            
    return ""

def _wikimedia_api(query):
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
        
        for page in pages.values():
            title_lower = page.get("title", "").lower()
            if any(bad in title_lower for bad in ZABRANJENE_RECI_U_NAZIVU):
                continue
            
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                info = imageinfo[0]
                if info.get("mime") in ("image/jpeg", "image/png"):
                    sirina = info.get("width", 0)
                    visina = info.get("height", 0)
                    if sirina >= 600 and visina >= 400:
                        return info.get("url", "")
    except Exception:
        pass
    return ""

def _openverse_api(query):
    url = "https://api.openverse.org/v1/images/"
    headers = {"User-Agent": USER_AGENT}
    params = {
        "q": query,
        "page_size": 10,
        "license_type": "commercial",
        "extension": "jpg",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            results = r.json().get("results", [])
            for result in results:
                title = (result.get("title") or "").lower()
                if any(bad in title for bad in ZABRANJENE_RECI_U_NAZIVU):
                    continue
                
                url_slike = result.get("url", "")
                if url_slike:
                    return url_slike
    except Exception:
        pass
    return ""