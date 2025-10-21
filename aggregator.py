import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# --- Configurazione ---
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/"
MAX_ARTICLES = 15 
FEED_JSON_PATH = 'feed.json'
INDEX_HTML_PATH = 'index.html'

# --- Parsing e Scraping (Logica Invariata) ---
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

# --- Scrittura HTML (LOGICA AGGIORNATA: SOSTITUZIONE BASATA SULL'ID DEL DIV) ---
def update_index_html(articles):
    """Aggiorna la sezione unica dei contenuti dinamici nel file index.html."""
    
    # Marcatori basati sull'ID del DIV in index.html
    div_id = 'all-articles'
    
    # 1. GENERATE ALL ARTICLES CONTENT (Lista Unica)
    list_html = ""
    for article in articles:
        link = article["link"] if article["link"] else "#"
        date_display = article["date"] if article["date"] else ""
        source_display = article["source"].replace(" (Fallback)", "") 

        # Layout griglia pulito: Data/Fonte su 1/4, Titolo su 3/4
        list_html += f'<div class="grid md:grid-cols-4 gap-6 items-start py-4 border-b border-napoli-card/50 hover:bg-napoli-card/20 p-2 -mx-2 rounded-lg transition-colors">\n'
        list_html += f'  <div class="md:col-span-1">\n'
        list_html += f'    <p class="text-sm text-napoli-white/60">{date_display}</p>\n'
        list_html += f'    <p class="text-primary font-semibold text-sm">{source_display}</p>\n'
        list_html += f'  </div>\n'
        list_html += f'  <div class="md:col-span-3">\n'
        list_html += f'    <a class="group block" href="{link}" target="_blank">\n'
        list_html += f'      <h3 class="text-xl font-bold text-napoli-white group-hover:text-primary transition-colors">{article["title"]}</h3>\n'
        list_html += f'    </a>\n'
        list_html += f'  </div>\n'
        list_html += f'</div>\n'

    # 2. Leggi il contenuto e trova il blocco da sostituire
    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f: 
            content = f.read()
    except FileNotFoundError: 
        return

    # Troviamo l'inizio e la fine del div in base all'ID per una sostituzione sicura.
    start_tag = f'<div id="{div_id}" class="space-y-2">'
    end_tag = '</div>' # Chiude il div con id="all-articles"
    
    start_index = content.find(start_tag)
    
    if start_index == -1:
        # Fallback alla sostituzione con marker se l'ID non è stato trovato (molto improbabile ora)
        start_marker = ''
        end_marker = ''
        start_index = content.find(start_marker)
        end_index = content.find(end_marker)
        
        if start_index != -1 and end_index != -1:
            final_content = content[:start_index + len(start_marker)] + "\n" + list_html.strip() + "\n" + content[end_index:]
        else:
            return # Nessun punto di inserimento trovato

    else:
        # Se l'ID è stato trovato, cerchiamo il tag di chiusura di quel div specifico.
        # Partiamo da DOPO il tag iniziale per evitare di trovare il tag di chiusura troppo presto.
        content_after_start = content[start_index + len(start_tag):]
        end_index_relative = content_after_start.find(end_tag)

        if end_index_relative != -1:
            # Calcoliamo l'indice assoluto della fine del div
            end_index_absolute = start_index + len(start_tag) + end_index_relative
            
            # Sostituiamo il contenuto tra il tag iniziale e il tag finale del DIV
            final_content = content[:start_index + len(start_tag)] + "\n" + list_html.strip() + "\n" + content[end_index_absolute:]
        else:
            return # Tag di chiusura non trovato

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
    
    if articles:
        try:
            with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
            
        update_index_html(articles)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    main()
