import feedparser
import os
import json
from datetime import datetime

# Lista RSS feedova lokalnih portala za Istočnu Srbiju
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

def prikupi_vesti():
    sve_vesti = []
    
    for url in RSS_FEEDS:
        print(f"Povezujem se na: {url}...")
        try:
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"  ⚠️ Greška pri čitanju feed-a: {url}")
                continue

            if not feed.entries:
                print(f"  ⚠️ Nema vesti u feed-u: {url}")
                continue

            for entry in feed.entries:
                vest = {
                    "naslov": entry.title,
                    "link": entry.link,
                    "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "izvor": url
                }
                sve_vesti.append(vest)
            
            print(f"  ✅ Pronađeno {len(feed.entries)} vesti.")
        
        except Exception as e:
            print(f"  ❌ Greška: {e}")
            continue

    # Pravimo folder 'content' ako ne postoji
    os.makedirs("content", exist_ok=True)
    
    # Čuvamo sve vesti u JSON fajl
    with open("content/vesti.json", "w", encoding="utf-8") as f:
        json.dump(sve_vesti, f, ensure_ascii=False, indent=4)
    
    print(f"\n📦 Ukupno sačuvano {len(sve_vesti)} vesti u content/vesti.json")

if __name__ == "__main__":
    prikupi_vesti()