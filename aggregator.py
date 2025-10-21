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

# --- Scrittura HTML (LOGICA FINALE: PULIZIA GLOBALE E INIEZIONE UNICA) ---
def update_index_html(articles):
    """Aggiorna la sezione unica dei contenuti dinamici nel file index.html."""
    
    all_articles_start, all_articles_end = '', ''

    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f: 
            content = f.read()
    except FileNotFoundError: 
        return
        
    updated_content = content

    # 1. GENERATE ALL ARTICLES CONTENT (Lista Unica)
    list_html = ""
    for article in articles:
        link = article["link"] if article["link"] else "#"
        date_display = article["date"] if article["date"] else ""
        source_display = article["source"].replace(" (Fallback)", "") 

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

    # 2. DEFINISCI IL BLOCCO DI SOSTITUZIONE COMPLETO
    # Questo è il blocco esatto che verrà iniettato, inclusi i marker.
    replacement_block = f'{all_articles_start}\n{list_html.strip()}\n{all_articles_end}'
    
    # 3. REGEX: TROVA TUTTE LE OCCORRENZE DEL BLOCCO E PULISCI
    # Il pattern cerca il marker di inizio, seguito da qualsiasi contenuto (non avido), fino al marker di fine.
    pattern = re.compile(rf'{re.escape(all_articles_start)}.*?{re.escape(all_articles_end)}', re.DOTALL)
    
    # 4. ESEGUI LA PULIZIA: Rimpiazza TUTTE le occorrenze del vecchio blocco (incluse quelle indesiderate) con il SOLO blocco di rimpiazzo.
    # Usiamo pattern.sub per sostituire tutte le occorrenze in una volta sola.
    final_content = pattern.sub(replacement_block, updated_content)

    # Questo assicura che se i marker sono duplicati (problema che genera l'iniezione doppia), 
    # l'intero blocco tra i marker venga rimpiazzato con il nuovo contenuto, in tutti i posti.
    # Tuttavia, se i marker sono duplicati, il risultato sarà comunque la duplicazione del contenuto.
    
    # Soluzione alternativa: Rimuovere tutti i blocchi tranne l'ultimo.
    # Eseguiamo la sostituzione globale (per pulire i vecchi contenuti), e poi ripristiniamo l'ultimo.
    
    # 3. BIS. PULIZIA TOTALE: Rimpiazza TUTTI i contenuti tra i marker con NULLA.
    # Usiamo come replacement solo i due marker senza contenuti in mezzo.
    clean_replacement = f'{all_articles_start}\n{all_articles_end}'
    
    # La REGEX con re.DOTALL cerca tutti i blocchi START...END nel file
    updated_content = pattern.sub(clean_replacement, updated_content)
    
    # 4. INIEZIONE UNICA: Adesso, il file contiene SOLO i marker puliti. Cerchiamo l'ULTIMA occorrenza (quella che si trova in <main>)
    # e iniettiamo il contenuto lì.

    # Troviamo l'indice dell'ULTIMO marker di START.
    last_start_index = updated_content.rfind(all_articles_start)
    
    if last_start_index != -1:
        # Troviamo l'indice del marker di END che segue questo START.
        last_end_index = updated_content.find(all_articles_end, last_start_index)
        
        if last_end_index != -1:
            # Sostituiamo il blocco START...END con il blocco contenente gli articoli.
            final_content = (
                updated_content[:last_start_index] + 
                replacement_block + 
                updated_content[last_end_index + len(all_articles_end):]
            )
        else:
            final_content = updated_content
    else:
        final_content = updated_content
    
    # 5. Scrivi il contenuto aggiornato
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
