import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# --- CONFIGURAZIONE ---

FALLBACK_URL = "https://sscnapoli.it/news/" 
FEED_JSON_PATH = 'feed.json'

# Filtro Temporale: Inizio stagione (1 Luglio 2025)
SEASON_START = datetime(2025, 7, 1)

MAX_ARTICLES_TO_SCRAPE = 200 


# ---------------------------
# UTILITY PER DATA E FILTRI
# ---------------------------

def _extract_scraping_date(date_str):
    """Estrae, parse la data DD/MM/YYYY e applica il filtro temporale."""
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            # Se la data è >= SEASON_START, è valida
            if date_obj >= SEASON_START:
                return date_obj, date_str
        except ValueError:
            pass # Data non valida o mancante, fallisce il filtro data
    # Se il parsing fallisce o se la data è precedente a SEASON_START
    return None, "Data Sconosciuta"

# ---------------------------
# FUNZIONE PRINCIPALE DI SCRAPING
# ---------------------------

def scraping_sscnapoli():
    """Esegue lo scraping delle notizie dal sito ufficiale SSC Napoli."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # Selettori per i container degli articoli del sito SSC Napoli
        containers = soup.select('div.elementor-posts-container article.elementor-post') \
                     or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in containers[:MAX_ARTICLES_TO_SCRAPE]:
            a_tag = item.select_one('h3.elementor-post__title a') or item.select_one('a[href]')
            if not a_tag: continue
            
            link = a_tag.get('href', '#')
            
            # Esclude link che puntano a file (es. PDF)
            if link.lower().endswith(('.pdf', '.doc', '.zip')):
                continue

            # Pulizia Titolo: estrae il testo e rimuove duplicazioni
            title = BeautifulSoup(a_tag.get_text().strip(), 'html.parser').get_text()
            title = re.sub(r'\s+', ' ', title.strip())
            
            parts = title.split()
            mid = len(parts) // 2
            if ' '.join(parts[:mid]) == ' '.join(parts[mid:]):
                title = ' '.join(parts[:mid])
                
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                title = "Senza titolo"

            # Estrazione data (DD/MM/YYYY)
            date_tag = item.select_one('span.elementor-post-date')
            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_tag.get_text().strip()) if date_tag else None
            
            # Tenta di estrarre e validare la data.
            date_obj, formatted_date = _extract_scraping_date(date_match.group(0) if date_match else None)
            
            # Se la data è None, significa che l'articolo è precedente a SEASON_START o non ha data valida.
            if date_obj is None: 
                continue 

            articles.append({
                'title': title, 
                'link': link, 
                'date': formatted_date, 
                'date_obj': date_obj, 
                'source': 'SSC Napoli (Ufficiale)' 
            }) 
        return articles
    except requests.RequestException as e:
        print(f"Errore di rete/richiesta: {e}")
        return []
    except Exception as e:
        print(f"Errore nello scraping: {e}")
        return []

# ---------------------------
# ESECUZIONE SCRIPT
# ---------------------------
def main():
    """Esegue lo scraping, l'ordinamento e il salvataggio."""
    
    all_articles = scraping_sscnapoli()
    
    if not all_articles:
        print(f"Nessun articolo trovato dal {SEASON_START.strftime('%d/%m/%Y')}.")
        # Salva un file vuoto se non ci sono dati recenti
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)
        return

    # Ordinamento: dal più recente al più datato
    all_articles.sort(key=lambda x: x.get('date_obj', datetime.min), reverse=True)
    
    # Rimuove l'oggetto 'date_obj' prima di salvare
    for article in all_articles:
        if 'date_obj' in article:
            del article['date_obj']

    try:
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, indent=4, ensure_ascii=False)
        print(f"Salvato {len(all_articles)} articoli in '{FEED_JSON_PATH}'.")
    except Exception as e:
        print(f"Errore durante il salvataggio di feed.json: {e}")

if __name__ == "__main__":
    main()
