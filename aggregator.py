import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# --- CONFIGURAZIONE ---

FALLBACK_URL = "https://sscnapoli.it/news/" 
FEED_JSON_PATH = 'feed.json'

# Filtro Temporale: Inizio stagione (1 Luglio 2025) - MANTENUTO CORRETTO
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
            pass
    return None, "Data Sconosciuta"

# ---------------------------
# FUNZIONE PRINCIPALE DI SCRAPING
# ---------------------------

def scraping_sscnapoli():
    """Esegue lo scraping delle notizie dal sito ufficiale SSC Napoli."""
    articles = []
    
    # 1. Recupero la pagina
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(FALLBACK_URL, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. SELETTORI POTENZIATI per i container degli articoli
        containers = soup.select('div.elementor-posts-container article.elementor-post') or \
                     soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card|hentry|post'))

        if not containers:
            print("ERRORE CRITICO: Nessun contenitore articolo trovato con i selettori attuali.")
            return []

        for item in containers[:MAX_ARTICLES_TO_SCRAPE]:
            # --- Link e Titolo ---
            # Cerca il link sia nell'h3 del titolo che in un generico <a> all'interno della card
            a_tag = item.select_one('h3 a') or item.select_one('a[href]')
            if not a_tag: continue
            
            link = a_tag.get('href', '#')
            if link.lower().endswith(('.pdf', '.doc', '.zip')):
                continue

            # Pulizia Titolo
            title = BeautifulSoup(a_tag.get_text().strip(), 'html.parser').get_text()
            title = re.sub(r'\s+', ' ', title.strip())
            
            parts = title.split()
            mid = len(parts) // 2
            if ' '.join(parts[:mid]) == ' '.join(parts[mid:]):
                title = ' '.join(parts[:mid])
                
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                title = "Senza titolo"

            # --- Data ---
            # Cerca la data in qualsiasi span o div che possa contenere una data
            date_tag = item.select_one('span.elementor-post-date') or \
                       item.select_one('span.post-date') or \
                       item.select_one('.date') or \
                       item.select_one('time')

            date_str = None
            if date_tag:
                # Estrai la stringa data (cerca il pattern DD/MM/YYYY)
                date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_tag.get_text().strip())
                if date_match:
                    date_str = date_match.group(0)
            
            # Applica il filtro data (season_start)
            date_obj, formatted_date = _extract_scraping_date(date_str)
            
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
        print(f"Errore di rete/richiesta (controlla l'URL): {e}")
        return []
    except Exception as e:
        print(f"Errore nello scraping (potrebbe essere la struttura cambiata): {e}")
        return []

# ---------------------------
# ESECUZIONE SCRIPT
# ---------------------------
def main():
    """Esegue lo scraping, l'ordinamento e il salvataggio."""
    
    print(f"Avvio scraping. Filtro data: >= {SEASON_START.strftime('%d/%m/%Y')}.")
    
    all_articles = scraping_sscnapoli()
    
    if not all_articles:
        print("Scraping completato: Nessun articolo recente trovato (o errore nello scraping).")
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
        print(f"SUCCESSO: Salvato {len(all_articles)} articoli in '{FEED_JSON_PATH}'.")
    except Exception as e:
        print(f"Errore durante il salvataggio di feed.json: {e}")

if __name__ == "__main__":
    main()
