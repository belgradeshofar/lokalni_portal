import feedparser
import sys

# Lista svih feedova za testiranje
FEEDS = {
    "Kurir - vesti": "https://www.kurir.rs/rss/vesti/",
    "Kurir - sve": "https://www.kurir.rs/rss/",
    "Novosti - sve vesti": "https://www.novosti.rs/rss/2-Sve%20vesti",
    "Novosti - politika": "https://www.novosti.rs/rss/1-Politika",
    "Alo - dnevne": "https://www.alo.rs/rss/danasnje_vesti",
    "Alo - sve": "https://www.alo.rs/rss/",
    "Blic - IT": "https://www.blic.rs/rss/IT",
    "Blic - sve": "https://www.blic.rs/rss/",
    "Telegraf - sve": "https://www.telegraf.rs/rss",
    "Telegraf - vesti": "https://www.telegraf.rs/rss/vesti",
    "Danas - sve": "https://www.danas.rs/feed/",
    "N1 - sve": "https://n1info.rs/feed/",
    "Google News - Blic": "https://news.google.com/rss/search?q=site:blic.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Telegraf": "https://news.google.com/rss/search?q=site:telegraf.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Kurir": "https://news.google.com/rss/search?q=site:kurir.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Alo": "https://news.google.com/rss/search?q=site:alo.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Novosti": "https://news.google.com/rss/search?q=site:novosti.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Danas": "https://news.google.com/rss/search?q=site:danas.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - N1": "https://news.google.com/rss/search?q=site:n1info.rs&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Politika": "https://news.google.com/rss/search?q=politika&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Hronika": "https://news.google.com/rss/search?q=hronika&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Sport": "https://news.google.com/rss/search?q=sport&hl=sr&gl=RS&ceid=RS:sr",
    "Google News - Ekonomija": "https://news.google.com/rss/search?q=ekonomija&hl=sr&gl=RS&ceid=RS:sr",
}

print("=" * 80)
print("TESTIRANJE RSS FEEDOVA")
print("=" * 80)

rezultati = {"radi": [], "ne_radi": []}

for naziv, url in FEEDS.items():
    try:
        feed = feedparser.parse(url)
        broj = len(feed.entries)
        if broj > 0:
            print(f"\n✅ RADI | {broj:3d} vesti | {naziv}")
            print(f"   URL: {url}")
            print(f"   Primer: {feed.entries[0].title[:90]}")
            rezultati["radi"].append((naziv, url, broj))
        else:
            print(f"\n❌ NE RADI | {naziv}")
            print(f"   URL: {url}")
            rezultati["ne_radi"].append((naziv, url))
    except Exception as e:
        print(f"\n💥 GRESKA | {naziv}")
        print(f"   URL: {url}")
        print(f"   Detalj: {e}")
        rezultati["ne_radi"].append((naziv, url))

print("\n" + "=" * 80)
print("REZIME")
print("=" * 80)
print(f"\n✅ Radi: {len(rezultati['radi'])}")
for naziv, url, broj in rezultati["radi"]:
    print(f"   - {naziv} ({broj} vesti)")

print(f"\n❌ Ne radi: {len(rezultati['ne_radi'])}")
for naziv, url in rezultati["ne_radi"]:
    print(f"   - {naziv}")

print("\n" + "=" * 80)
print("KOPIRAJ OVAJ DEO I POSALJI MI GA:")
print("=" * 80)
print("\n--- RADI ---")
for naziv, url, broj in rezultati["radi"]:
    print(f"{naziv} | {url} | {broj} vesti")
print("\n--- NE RADI ---")
for naziv, url in rezultati["ne_radi"]:
    print(f"{naziv} | {url}")