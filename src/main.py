import feedparser

def prikupi_vesti():
    # Ovde ćemo kasnije staviti prave lokalne portale. 
    # Za test, koristimo BBC RSS kao primer da vidimo da li radi.
    rss_url = "http://feeds.bbci.co.uk/news/rss.xml"
    
    print(f"Povezujem se na: {rss_url}...")
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        print("Greška pri čitanju feed-a.")
        return

    print(f"Pronađeno {len(feed.entries)} vesti.\n")
    
    for entry in feed.entries[:3]: # Uzimamo samo prve 3 za test
        print(f"NASLOV: {entry.title}")
        print(f"LINK: {entry.link}")
        print("-" * 40)

if __name__ == "__main__":
    prikupi_vesti()