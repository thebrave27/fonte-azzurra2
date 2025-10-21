import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# --- Configurazione ---
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/"
MAX_ARTICLES = 25 # Aumentato il limite per avere più notizie
FEED_JSON_PATH = 'feed.json'

# --- Parsing e Scraping ---
def parse_rss():
    """Tenta di analizzare il feed RSS di Fonte Azzurra."""
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        entries = []
        for entry in feed.entries[:MAX_ARTICLES]:
            title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
            date_str = getattr(entry, 'published', getattr(entry, 'updated', ''))
            
            if date_str:
                try:
                    # Tenta di analizzare la data da feedparser
                    date_obj = datetime(*entry.published_parsed[:6])
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except Exception:
                    # Fallback a una data vuota se l'analisi fallisce
                    formatted_date = ""
            else:
                formatted_date = ""

            entries.append({
                'title': title, 
                'link': entry.link, 
                'date': formatted_date, 
                'source': 'Fonte Azzurra'
            })
        return entries if entries else None
    except Exception:
        return None

def scraping_fallback():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_containers = soup.select('div.elementor-posts-container article.elementor-post') or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in article_containers[:MAX_ARTICLES]:
            a_tag = item.select_one('h3.elementor-post__title a') or item.select_one('a[href]')
            if not a_tag: continue
            
            link = a_tag['href']
            title = re.sub(r'\s+', ' ', a_tag.get_text().strip()).strip()
            
            # Pulizia duplicati nel titolo (logica conservata)
            title_parts = title.split()
            mid_point = len(title_parts) // 2
            first_half = ' '.join(title_parts[:mid_point])
            if first_half and first_half == ' '.join(title_parts[mid_point:]):
                title = first_half
                
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                 title = "Senza titolo"

            date_tag = item.select_one('div.elementor-post__meta-data span.elementor-post-date')
            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_tag.get_text().strip()) if date_tag else None
            formatted_date = date_match.group(0) if date_match else ""

            articles.append({
                'title': title, 
                'link': link, 
                'date': formatted_date, 
                'source': 'SSC Napoli (Fallback)' # Manteniamo (Fallback) per tracciamento, verrà rimosso dal JS
            }) 
        return articles
    except Exception:
        return []

# --- Funzione Principale: Solo JSON ---
def main():
    articles = parse_rss()
    if not articles: articles = scraping_fallback()
    
    # Se abbiamo articoli, salviamo SOLO il file JSON.
    if articles:
        try:
            with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
        except Exception as e:
            # Stampa l'errore per il debug se il salvataggio fallisce
            print(f"Errore durante il salvataggio di feed.json: {e}")
# ----------------------------------------------------------------------

if __name__ == "__main__":
    main()
