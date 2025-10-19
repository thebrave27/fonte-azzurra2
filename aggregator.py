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

def parse_rss():
    """Tenta di analizzare il feed RSS di Fonte Azzurra."""
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

def scraping_fallback():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    print(f"🧩 Fallback attivo: estraggo articoli dal sito SSC Napoli da {FALLBACK_URL}...")
    articles = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(FALLBACK_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Selettori flessibili per i contenitori degli articoli su /news/
        article_containers = soup.find_all(
            ['div', 'article'], 
            class_=re.compile(r'elementor-post__card|post-card|news-item|post')
        )
        
        if not article_containers:
            article_containers = soup.select('div.elementor-posts-container article')
            
            if not article_containers:
                print("❌ Errore nello scraping: Fallito il selettore generico.")
                return articles


        for item in article_containers[:MAX_ARTICLES]:
            
            # Estrazione Link
            a_tag = item.find('a', href=True)
            if not a_tag:
                a_tag = item.select_one('a[href]')
                if not a_tag:
                    continue
            
            link = a_tag['href']
            
            # Estrazione Titolo (più robusta)
            title_tag = item.find(['h2', 'h3', 'h4'], class_=re.compile(r'title|post-title|news-title'))
            
            if not title_tag:
                title = a_tag.get_text().strip()
            else:
                title = title_tag.get_text().strip()

            title = re.sub(r'\s+', ' ', title).strip()
            if not title or title.lower() in ['leggi tutto', 'read more']:
                 title = "Senza titolo (Estratto dal link)"


            # Estrazione Data
            date_tag = item.find(['span', 'div', 'time', 'p'], class_=re.compile(r'date|article-date|post-date|meta-date'))
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

def save_to_json(data):
    """Salva i dati estratti nel file JSON."""
    try:
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"📝 Dati salvati con successo in {FEED_JSON_PATH}")
    except Exception as e:
        print(f"❌ Errore nel salvataggio del JSON: {e}")

def update_index_html(articles):
    """Aggiorna la sezione dei contenuti dinamici nel file index.html usando indici di stringa (anti-duplicazione)."""
    
    start_tag = ''
    end_tag = ''

    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Errore: {INDEX_HTML_PATH} non trovato. Impossibile aggiornare.")
        return

    # 1. Trova le posizioni dei tag
    start_index = content.find(start_tag)
    end_index = content.find(end_tag)

    if start_index == -1 or end_index == -1:
        print("⚠️ Attenzione: I tag di sostituzione dinamica non sono presenti in index.html.")
        return

    # 2. Crea il nuovo contenuto HTML
    new_content_html = ""
    for article in articles:
        link = article["link"] if article["link"] else "#"
        new_content_html += f'<li><a href="{link}" target="_blank">{article["title"]}</a> <small>({article["date"]})</small></li>\n'
    
    # 3. Costruisci il nuovo contenuto completo con la sostituzione
    # Parte 1: Inizio del file fino alla fine del tag START
    updated_content = content[:start_index + len(start_tag)]
    
    # Parte 2: Inserimento del nuovo contenuto dinamico
    updated_content += "\n" + new_content_html.strip() + "\n"
    
    # Parte 3: Aggiungi il tag END e il resto del file
    updated_content += content[end_index:]

    # 4. Scrivi il contenuto aggiornato
    try:
        with open(INDEX_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"📝 {INDEX_HTML_PATH} aggiornato con successo.")
    except Exception as e:
        print(f"❌ Errore nella scrittura di {INDEX_HTML_PATH}: {e}")

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
