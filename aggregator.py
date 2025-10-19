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

# ----------------------------------------------------------------------
# FUNZIONE PARSING RSS (Fonte Azzurra) - INVARIATA
# ----------------------------------------------------------------------
def parse_rss():
    """Tenta di analizzare il feed RSS di Fonte Azzurra."""
    print("🔵 Avvio aggiornamento Fonte Azzurra...")
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        entries = []
        for entry in feed.entries[:MAX_ARTICLES]:
            # Pulisce il titolo da eventuali tag HTML
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

            entries.append({
                'title': title,
                'link': entry.link,
                'date': formatted_date,
                'source': 'Fonte Azzurra'
            })
        
        if entries:
            print(f"✅ Estratti {len(entries)} articoli da Fonte Azzurra.")
            return entries
        
        print("⚠️ Nessun articolo trovato nel feed RSS. Passaggio al fallback.")
        return None

    except Exception as e:
        print(f"❌ Errore nel parsing RSS: {e}")
        print("Passaggio al fallback.")
        return None

# ----------------------------------------------------------------------
# FUNZIONE SCRAPING FALLBACK (SSC Napoli) - INVARIATA
# ----------------------------------------------------------------------
def scraping_fallback():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    print(f"🧩 Fallback attivo: estraggo articoli dal sito SSC Napoli da {FALLBACK_URL}...")
    articles = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(FALLBACK_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Selettori per articoli
        article_containers = soup.select('div.elementor-posts-container article.elementor-post')
        
        if not article_containers:
            article_containers = soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))
            if not article_containers:
                 return articles

        for item in article_containers[:MAX_ARTICLES]:
            
            title_h3 = item.select_one('h3.elementor-post__title')
            if title_h3:
                a_tag = title_h3.find('a', href=True)
            else:
                 a_tag = item.select_one('a[href]')
            if not a_tag:
                continue
            
            link = a_tag['href']
            title = a_tag.get_text().strip()
            title = re.sub(r'\s+', ' ', title).strip()
            
            # LOGICA DI PULIZIA: Rimuove la duplicazione del titolo
            title_parts = title.split()
            mid_point = len(title_parts) // 2
            first_half = ' '.join(title_parts[:mid_point])
            second_half = ' '.join(title_parts[mid_point:])

            if first_half and second_half and first_half == second_half:
                title = first_half
                
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                 title = "Senza titolo (ESTRAZIONE FALLITA)"

            # Estrazione Data
            date_tag = item.select_one('div.elementor-post__meta-data span.elementor-post-date')
            date_str = date_tag.get_text().strip() if date_tag else ""
            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_str)
            formatted_date = date_match.group(0) if date_match else ""

            articles.append({
                'title': title,
                'link': link,
                'date': formatted_date,
                'source': 'SSC Napoli (Fallback)'
            })

        print(f"✅ Estratti {len(articles)} articoli.")
        return articles

    except requests.exceptions.RequestException as e:
        print(f"❌ Errore nella richiesta HTTP durante il fallback: {e}")
    except Exception as e:
        print(f"❌ Errore generico nello scraping: {e}")
        
    return articles

# ----------------------------------------------------------------------
# FUNZIONI DI SCRITTURA FILE (LOGICA AGGIORNATA)
# ----------------------------------------------------------------------
def save_to_json(data):
    """Salva i dati estratti nel file JSON."""
    try:
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"📝 Dati salvati con successo in {FEED_JSON_PATH}")
    except Exception as e:
        print(f"❌ Errore nel salvataggio del JSON: {e}")

def update_index_html(articles):
    """Aggiorna le due sezioni dei contenuti dinamici nel file index.html."""
    
    # Marcatori per Featured Content (Top 3)
    featured_start = ''
    featured_end = ''
    
    # Marcatori per Full List (Articoli 4-10)
    list_start = ''
    list_end = ''

    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Errore: {INDEX_HTML_PATH} non trovato. Impossibile aggiornare.")
        return
        
    updated_content = content

    # 1. GENERATE FEATURED CONTENT (Top 3 Riquadri)
    featured_html = ""
    for article in articles[:3]:
        link = article["link"] if article["link"] else "#"
        # HTML per card in evidenza (grandi)
        featured_html += f'<div class="bg-napoli-card p-6 rounded-xl shadow-2xl hover:shadow-3xl transition-all duration-300 transform hover:scale-[1.02]">\n'
        featured_html += f'  <a href="{link}" target="_blank" class="block group space-y-3">\n'
        featured_html += f'    <p class="text-sm font-semibold text-napoli-text/70">{article["date"]} <span class="ml-2 text-napoli-white">| IN EVIDENZA</span></p>\n'
        featured_html += f'    <h3 class="text-xl md:text-2xl font-bold text-napoli-text group-hover:text-napoli-white transition-colors duration-200">{article["title"]}</h3>\n'
        featured_html += f'  </a>\n'
        featured_html += f'</div>\n'
    
    # Sostituzione per il blocco FEATURED
    start_index = updated_content.find(featured_start)
    end_index = updated_content.find(featured_end)
    if start_index != -1 and end_index != -1:
        updated_content = updated_content[:start_index + len(featured_start)]
        updated_content += "\n" + featured_html.strip() + "\n"
        updated_content += updated_content[end_index:]
    
    # 2. GENERATE FULL LIST CONTENT (Articoli 4-10 con Immagine Placeholder)
    list_html = ""
    for article in articles[3:MAX_ARTICLES]:
        link = article["link"] if article["link"] else "#"
        # HTML per l'articolo in lista (con placeholder immagine)
        list_html += f'<div class="grid grid-cols-[80px_1fr] gap-4 py-4 hover:bg-napoli-card/30 rounded-lg p-2 -mx-2 transition-colors duration-150">\n'
        # Placeholder Immagine (un blocco blu con un'icona per indicare l'assenza di foto)
        list_html += f'  <div class="w-[80px] h-[60px] bg-napoli-text/50 rounded-lg flex items-center justify-center shrink-0">\n'
        list_html += f'    <svg class="w-6 h-6 text-napoli-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4-4 4 4m0 0l4-4 4 4m-4-4v4m0-8h.01"></path></svg>\n'
        list_html += f'  </div>\n'
        # Titolo e Meta
        list_html += f'  <div>\n'
        list_html += f'    <a href="{link}" target="_blank" class="group block">\n'
        list_html += f'      <h3 class="text-lg font-bold text-napoli-white group-hover:text-napoli-text transition-colors duration-200 leading-tight">{article["title"]}</h3>\n'
        list_html += f'    </a>\n'
        list_html += f'    <p class="text-xs mt-1 text-napoli-text/70">{article["date"]} | {article["source"]}</p>\n'
        list_html += f'  </div>\n'
        list_html += f'</div>\n'

    # Sostituzione per il blocco LIST
    list_start_index = updated_content.find(list_start)
    list_end_index = updated_content.find(list_end)
    
    if list_start_index != -1 and list_end_index != -1:
        final_content = updated_content[:list_start_index + len(list_start)]
        final_content += "\n" + list_html.strip() + "\n"
        final_content += updated_content[list_end_index:]
    else:
        final_content = updated_content


    # 3. Scrivi il contenuto aggiornato
    try:
        with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"📝 {INDEX_HTML_PATH} aggiornato con successo.")
    except Exception as e:
        print(f"❌ Errore nella scrittura di {INDEX_HTML_PATH}: {e}")

# ----------------------------------------------------------------------
# FUNZIONE PRINCIPALE - INVARIATA
# ----------------------------------------------------------------------
def main():
    """Funzione principale per l'esecuzione."""
    
    articles = parse_rss()
    
    if not articles:
        articles = scraping_fallback()

    if articles:
        save_to_json(articles)
        update_index_html(articles)
    else:
        print("🔴 Nessun articolo estratto. I file non saranno modificati.")


if __name__ == "__main__":
    main()
