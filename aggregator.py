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
# FUNZIONE PARSING RSS (Fonte Azzurra)
# ----------------------------------------------------------------------
def parse_rss():
    """Tenta di analizzare il feed RSS di Fonte Azzurra."""
    # ... (Il codice di parse_rss() rimane invariato) ...
    print("🔵 Avvio aggiornamento Fonte Azzurra...")
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
# FUNZIONE SCRAPING FALLBACK (SSC Napoli) - CON CORREZIONE DUPLICAZIONE
# ----------------------------------------------------------------------
def scraping_fallback():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    # ... (Il codice di scraping_fallback() rimane invariato) ...
    print(f"🧩 Fallback attivo: estraggo articoli dal sito SSC Napoli da {FALLBACK_URL}...")
    articles = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(FALLBACK_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        article_containers = soup.select('div.elementor-posts-container article.elementor-post')
        
        if not article_containers:
            print("❌ Errore nello scraping: Fallito il selettore container primario.")
            article_containers = soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))
            if not article_containers:
                 print("❌ Errore nello scraping: Fallito anche il selettore generico di card.")
                 return articles


        for item in article_containers[:MAX_ARTICLES]:
            
            # 1. Estrazione Link e Titolo
            title_h3 = item.select_one('h3.elementor-post__title')
            
            if title_h3:
                a_tag = title_h3.find('a', href=True)
            else:
                 a_tag = item.select_one('a[href]')


            if not a_tag:
                continue
            
            link = a_tag['href']
            
            # 2. Estrazione Titolo
            title = a_tag.get_text().strip()
            
            # Pulizia generale del titolo
            title = re.sub(r'\s+', ' ', title).strip()
            
            # LOGICA DI PULIZIA: Rimuove la duplicazione del titolo (es. "Titolo Titolo")
            title_parts = title.split()
            mid_point = len(title_parts) // 2
            first_half = ' '.join(title_parts[:mid_point])
            second_half = ' '.join(title_parts[mid_point:])

            if first_half and second_half and first_half == second_half:
                title = first_half
                print(f"🗑️ Titolo duplicato rimosso: {title}")
                
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                 title = "Senza titolo (ESTRAZIONE FALLITA)"


            # 3. Estrazione Data
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

        print(f"✅ Estratti {len(articles)} articoli:")
        for article in articles:
            if not article['link']:
                 article['link'] = "#"
            print(f"- {article['title']} ({article['link']})")
            
        return articles

    except requests.exceptions.RequestException as e:
        print(f"❌ Errore nella richiesta HTTP durante il fallback: {e}")
    except Exception as e:
        print(f"❌ Errore generico nello scraping: {e}")
        
    return articles

# ----------------------------------------------------------------------
# FUNZIONI DI SCRITTURA FILE (Logica Anti-Duplicazione)
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
    """Aggiorna la sezione dei contenuti dinamici nel file index.html (Output come Card)."""
    
    start_tag = ''
    end_tag = ''

    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Errore: {INDEX_HTML_PATH} non trovato. Impossibile aggiornare.")
        return

    start_index = content.find(start_tag)
    end_index = content.find(end_tag)

    if start_index == -1 or end_index == -1:
        print("⚠️ Attenzione: I tag di sostituzione dinamica non sono presenti in index.html.")
        return

    # 2. Crea il nuovo contenuto HTML con CLASSI TAILWIND
    new_content_html = ""
    for article in articles:
        link = article["link"] if article["link"] else "#"
        
        # Genera il blocco HTML per la Card
        new_content_html += f'<div class="bg-napoli-card p-4 rounded-lg shadow-xl hover:shadow-2xl transition-all duration-300">\n'
        new_content_html += f'  <a href="{link}" target="_blank" class="block group">\n'
        new_content_html += f'    <h3 class="text-xl font-bold text-napoli-text group-hover:text-napoli-white transition-colors duration-200">{article["title"]}</h3>\n'
        new_content_html += f'  </a>\n'
        new_content_html += f'  <p class="text-sm mt-1 text-napoli-text/70">{article["date"]} <span class="font-semibold ml-2 text-napoli-text">{article["source"]}</span></p>\n'
        new_content_html += f'</div>\n'
    
    # 3. Costruisci il nuovo contenuto completo con la sostituzione sicura
    updated_content = content[:start_index + len(start_tag)]
    updated_content += "\n" + new_content_html.strip() + "\n"
    updated_content += content[end_index:]

    # 4. Scrivi il contenuto aggiornato
    try:
        with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"📝 {INDEX_HTML_PATH} aggiornato con successo.")
    except Exception as e:
        print(f"❌ Errore nella scrittura di {INDEX_HTML_PATH}: {e}")

# ----------------------------------------------------------------------
# FUNZIONE PRINCIPALE
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
