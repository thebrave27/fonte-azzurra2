import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
from itertools import chain # Per unire liste

# --- Configurazione ---
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/"
MAX_ARTICLES_PER_SOURCE = 12 # Numero massimo di articoli per ogni fonte
FEED_JSON_PATH = 'feed.json'

# Lista di domini di fonti terze affidabili per le interviste
INTERVIEW_DOMAINS = [
    "sport.sky.it", 
    "dazn.com", 
    "gazzetta.it", 
    "corrieredellosport.it",
    "calciomercato.com"
]

# --- Funzioni di Parsing e Scraping (Invariate) ---

def parse_rss():
    """Tenta di analizzare il feed RSS di Fonte Azzurra."""
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        entries = []
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            # ... (Logica di parsing RSS esistente) ...
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
        return entries
    except Exception:
        return []

def scraping_fallback():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # Utilizza un selettore più generico per i contenitori di articoli
        article_containers = soup.select('div.elementor-posts-container article.elementor-post') or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in article_containers[:MAX_ARTICLES_PER_SOURCE]:
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
                'source': 'SSC Napoli' # Rimosso (Fallback) qui, il JS lo gestisce, ma lo teniamo pulito
            }) 
        return articles
    except Exception:
        return []

# --- NUOVA FUNZIONE: Ricerca e Aggregazione Interviste ---
def search_third_party_interviews():
    """
    Esegue una ricerca mirata su Google per trovare interviste/dichiarazioni.
    
    NOTA: Questa funzione è un placeholder. L'uso diretto della funzione Google:search 
    in un ambiente GitHub Actions per scraping richiede una Custom Search API Key e 
    un setup che va oltre lo scopo di un semplice script Python.
    
    Per ora, il modo più efficiente per implementare questa fase due è 
    aggiungere un ulteriore scraping mirato o l'integrazione di feed RSS secondari.
    Qui aggiungiamo una logica di ricerca basata su un motore di ricerca generico 
    per simulare l'aggregazione di titoli di interviste.
    """
    interview_articles = []
    
    # Costruiamo la query di ricerca che usa le virgolette e cerca sui domini specificati
    # Esempio: "Giocatore Napoli" AND ("dichiarazioni" OR "intervista") site:sky.it OR site:dazn.com...
    
    # Questa query è un esempio e dovrebbe essere eseguita utilizzando un servizio di ricerca web.
    search_query = '("Napoli" AND ("dichiarazioni" OR "intervista" OR "parole di"))'
    site_query = " OR ".join([f"site:{d}" for d in INTERVIEW_DOMAINS])
    final_query = f"{search_query} ({site_query})"
    
    # Poiché non possiamo eseguire un tool di ricerca web diretto qui senza API Key,
    # qui è dove il codice si fermerebbe.
    # Se il tool google:search fosse disponibile, la chiamata sarebbe:
    # try:
    #    results = google:search.query(queries=[final_query])
    #    for result in results:
    #        interview_articles.append({
    #            'title': result['title'],
    #            'link': result['link'],
    #            'date': '', # Data spesso non disponibile direttamente dal titolo
    #            'source': result['source'] # Esempio: Sky Sport, Gazzetta
    #        })
    # except Exception:
    #    pass
    
    # Per ora, restituiamo una lista vuota o aggiungiamo un feed RSS secondario se disponibile.
    # Dato che l'utente ha richiesto un aggregatore, suggerisco di trovare un feed RSS di 
    # notizie sul Napoli da una fonte terza (ad es. un giornale sportivo).
    
    # Aggiungiamo un placeholder per il feed RSS della Gazzetta, se esiste
    GAZZETTA_NAPOLI_FEED = "https://www.gazzetta.it/rss/napoli.xml"
    
    try:
        gazzetta_feed = feedparser.parse(GAZZETTA_NAPOLI_FEED)
        for entry in gazzetta_feed.entries[:MAX_ARTICLES_PER_SOURCE // 2]:
            title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
            # Filtriamo solo articoli che sembrano essere interviste/dichiarazioni
            if any(kw in title.lower() for kw in ["parole", "intervista", "dichiarazioni", "ha detto"]):
                 
                date_str = getattr(entry, 'published', getattr(entry, 'updated', ''))
                if date_str:
                    try:
                        date_obj = datetime(*entry.published_parsed[:6])
                        formatted_date = date_obj.strftime("%d/%m/%Y")
                    except Exception:
                        formatted_date = ""
                else:
                    formatted_date = ""

                interview_articles.append({
                    'title': title, 
                    'link': entry.link, 
                    'date': formatted_date, 
                    'source': 'Gazzetta dello Sport'
                })
    except Exception:
        pass
        
    return interview_articles

# --- Funzione Principale: Aggregazione Finale ---
def main():
    # Raccolta da fonte principale
    official_articles = parse_rss()
    if not official_articles: official_articles = scraping_fallback()

    # Raccolta da fonti terze (Fase Due)
    interview_articles = search_third_party_interviews()
    
    # Unione di tutte le liste
    all_articles = list(chain(official_articles, interview_articles))

    # Salviamo tutti gli articoli nel file JSON
    if all_articles:
        try:
            with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_articles, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Errore durante il salvataggio di feed.json: {e}")

if __name__ == "__main__":
    main()
