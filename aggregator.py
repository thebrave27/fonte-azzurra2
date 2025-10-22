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
# Dato che non ci sono limiti di RSS, impostiamo un limite alto per lo scraping
MAX_ARTICLES_TO_SCRAPE = 200 


# ---------------------------
# UTILITY PER DATA E FILTRI
# ---------------------------

def _extract_scraping_date(date_str):
    """Estrae, parse la data DD/MM/YYYY e applica il filtro temporale."""
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            # Applica il filtro: se la data è >= SEASON_START, è valida
            if date_obj >= SEASON_START:
                return date_obj, date_str
        except ValueError:
            pass # Data non valida
    return None, "Data Sconosciuta"

# ---------------------------
# FUNZIONE PRINCIPALE DI SCRAPING
# ---------------------------

def scraping_sscnapoli():
    """Esegue lo scraping delle notizie dal sito ufficiale SSC Napoli."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Per un archivio più profondo, potremmo dover ciclare tra le pagine, 
        # ma per ora ci limitiamo alla prima pagina caricata (fino a MAX_ARTICLES_TO_SCRAPE)
        response = requests.get(FALLBACK_URL, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # Selettori per i container degli articoli del sito SSC Napoli
        containers = soup.select('div.elementor-posts-container article.elementor-post') \
                     or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in containers[:MAX_ARTICLES_TO_SCRAPE]:
            a_tag = item.select_one('h3.elementor-post__title a') or item.select_one('a[href]')
            if not a_tag: continue
            
            link = a_tag['href']
            # Pulisce spazi multipli nel titolo
            title = re.sub(r'\s+', ' ', a_tag.get_text().strip())
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                title = "Senza titolo"

            # Estrazione data in formato DD/MM/YYYY
            date_tag = item.select_one('div.elementor-post__meta-data span.elementor-post-date')
            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_tag.get_text().strip()) if date_tag else None
            
            date_obj, formatted_date = _extract_scraping_date(date_match.group(0) if date_match else None)
            
            # Se la data è None, significa che l'articolo è troppo vecchio (precedente a SEASON_START)
            if date_obj is None: 
                # Potremmo fermare l'aggregazione qui se gli articoli sono già ordinati sul sito, 
                # ma per sicurezza, continuiamo a scorrere il limite MAX_ARTICLES_TO_SCRAPE
                continue 

            articles.append({
                'title': title, 
                'link': link, 
                'date': formatted_date, 
                'date_obj': date_obj, # Usato per l'ordinamento finale
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
        print("Nessun articolo trovato per la stagione.")
        # Salva un file vuoto in caso di errore per non rompere il frontend
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)
        return

    # Ordinamento: dal più recente al più datato
    all_articles.sort(key=lambda x: x.get('date_obj', datetime.min), reverse=True)
    
    # Rimuove l'oggetto 'date_obj' prima di salvare in JSON
    for article in all_articles:
        if 'date_obj' in article:
            del article['date_obj']

    # Salvataggio
    try:
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, indent=4, ensure_ascii=False)
        print(f"Salvato {len(all_articles)} articoli in '{FEED_JSON_PATH}'.")
    except Exception as e:
        print(f"Errore durante il salvataggio di feed.json: {e}")

if __name__ == "__main__":
    main()
