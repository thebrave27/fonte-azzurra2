import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# --- Config ---
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/"
MAX_ARTICLES = 10
FEED_JSON_PATH = "feed.json"
INDEX_HTML_PATH = "index.html"

# --- Parsing RSS ---
def parse_rss():
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        entries = []
        for entry in feed.entries[:MAX_ARTICLES]:
            title = BeautifulSoup(entry.title, "html.parser").get_text().strip()
            date_str = getattr(entry, "published", getattr(entry, "updated", ""))
            formatted_date = ""
            if date_str and hasattr(entry, "published_parsed"):
                try:
                    date_obj = datetime(*entry.published_parsed[:6])
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except Exception:
                    pass
            entries.append({
                "title": title,
                "link": entry.link,
                "date": formatted_date,
                "source": "SSC Napoli"
            })
        return entries if entries else None
    except Exception:
        return None

# --- Scraping fallback (quando RSS non funziona) ---
def scraping_fallback():
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_containers = soup.select('article.elementor-post') or soup.find_all('div', class_=re.compile('post'))

        for item in article_containers[:MAX_ARTICLES]:
            a_tag = item.select_one('h3 a') or item.select_one('a[href]')
            if not a_tag:
                continue

            title = re.sub(r'\s+', ' ', a_tag.get_text().strip())
            title = re.sub(r'\(Fallback\)', '', title).strip()

            link = a_tag.get('href', '#')
            date_tag = item.select_one('time, span.elementor-post-date')
            formatted_date = date_tag.get_text(strip=True) if date_tag else ""

            articles.append({
                "title": title,
                "link": link,
                "date": formatted_date,
                "source": "SSC Napoli"
            })
        return articles
    except Exception as e:
        print("⚠️ Errore scraping:", e)
        return []

# --- Aggiornamento HTML ---
def update_index_html(articles):
    try:
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ index.html non trovato.")
        return

    # Genera i blocchi HTML per ogni articolo
    articles_html = ""
    for art in articles:
        date_display = f'<p class="text-sm text-primary/80">{art["date"]}</p>' if art["date"] else ""
        articles_html += f"""
        <div class="bg-card p-5 rounded-xl shadow hover:shadow-lg transition">
            <a href="{art['link']}" target="_blank" class="block group">
                {date_display}
                <h3 class="text-lg font-semibold text-white group-hover:text-primary transition-colors">
                    {art['title']}
                </h3>
            </a>
        </div>
        """

    # Sostituisci il contenuto nel div #all-articles
    new_content = re.sub(
        r'(<div id="all-articles"[^>]*>)(.*?)(</div>)',
        rf'\1\n{articles_html}\n\3',
        content,
        flags=re.DOTALL
    )

    with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("✅ index.html aggiornato con successo.")

# --- MAIN ---
def main():
    articles = parse_rss()
    if not articles:
        articles = scraping_fallback()
    if not articles:
        print("⚠️ Nessun articolo trovato.")
        return

    with open(FEED_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    update_index_html(articles)

if __name__ == "__main__":
    main()
