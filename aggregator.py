import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# --- Configurazione Corretta ---
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/"
MAX_ARTICLES = 10
FEED_JSON_PATH = 'feed.json'
INDEX_HTML_PATH = 'index.html'

# --- Parsing e Scraping (INVARIANTI) ---
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
                    date_obj = datetime(*entry.published_parsed[:6])
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except Exception:
                    formatted_date = ""
            else:
                formatted_date = ""

            entries.append({'title': title, 'link': entry.link, 'date': formatted_date, 'source': 'Fonte Azzurra'})
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
            
            # Pulizia duplicati
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

            articles.append({'title': title, 'link': link, 'date': formatted_date, 'source': 'SSC Napoli (Fallback)'})
        return articles
    except Exception:
        return []

# --- Scrittura HTML (LOGICA AGGIORNATA) ---
def update_index_html(articles):
    """Aggiorna le due sezioni dei contenuti dinamici nel file index.html."""
    
    featured_start, featured_end = '', ''
    list_start, list_end = '', ''

    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f: content = f.read()
    except FileNotFoundError: return
        
    updated_content = content

    # 1. GENERATE FEATURED CONTENT (Top 3 Riquadri)
    featured_html = ""
    for article in articles[:3]:
        link = article["link"] if article["link"] else "#"
        featured_html += f'<div class="bg-napoli-card p-6 rounded-xl shadow-2xl hover:shadow-3xl transition-all duration-300 transform hover:scale-[1.02]">\n'
        featured_html += f'  <a href="{link}" target="_blank" class="block group space-y-3">\n'
        date_display = article["date"] if article["date"] else ""
        featured_html += f'    <p class="text-sm font-semibold text-napoli-text/70">{date_display} <span class="ml-2 text-napoli-white">| IN EVIDENZA</span></p>\n'
        featured_html += f'    <h3 class="text-xl md:text-2xl font-bold text-napoli-text group-hover:text-napoli-white transition-colors duration-200">{article["title"]}</h3>\n'
        featured_html += f'  </a>\n'
        featured_html += f'</div>\n'
    
    # Sostituzione per il blocco FEATURED
    start_index = updated_content.find(featured_start)
    end_index = updated_content.find(featured_end)
    if start_index != -1 and end_index != -1:
        updated_content = updated_content[:start_index + len(featured_start)] + "\n" + featured_html.strip() + "\n" + updated_content[end_index:]
    
    # 2. GENERATE FULL LIST CONTENT (Articoli 4-10 - Card Semplice)
    list_html = ""
    for article in articles[3:MAX_ARTICLES]:
        link = article["link"] if article["link"] else "#"
        # Card semplice per la lista completa
        list_html += f'<div class="bg-napoli-card p-4 rounded-lg shadow-md hover:shadow-xl transition-all duration-300">\n'
        list_html += f'  <a href="{link}" target="_blank" class="block group">\n'
        list_html += f'    <h3 class="text-lg font-bold text-napoli-white group-hover:text-napoli-text transition-colors duration-200">{article["title"]}</h3>\n'
        list_html += f'  </a>\n'
        date_display = article["date"] if article["date"] else ""
        list_html += f'  <p class="text-xs mt-1 text-napoli-text/70">{date_display} <span class="font-semibold ml-2 text-napoli-text">| {article["source"]}</span></p>\n'
        list_html += f'</div>\n'

    # Sostituzione per il blocco LIST
    list_start_index = updated_content.find(list_start)
    list_end_index = updated_content.find(list_end)
    
    if list_start_index != -1 and list_end_index != -1:
        final_content = updated_content[:list_start_index + len(list_start)] + "\n" + list_html.strip() + "\n" + updated_content[list_end_index:]
    else:
        final_content = updated_content

    # 3. Scrivi il contenuto aggiornato
    try:
        with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(final_content)
    except Exception:
        pass

# ----------------------------------------------------------------------
def main():
    articles = parse_rss()
    if not articles: articles = scraping_fallback()
    if articles: update_index_html(articles)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    main()
