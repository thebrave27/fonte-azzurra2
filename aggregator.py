import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
from itertools import chain

# --- Configurazione Generale ---
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/" 

# LIMITE DI ARTICOLI PER FONTE (25 come richiesto)
MAX_ARTICLES_PER_SOURCE = 25 
FEED_JSON_PATH = 'feed.json'

# --- URL dei Feed RSS di Terze Parti ---
THIRD_PARTY_FEEDS = {
    # Giornali Sportivi (Specifici/Generici)
    'Gazzetta dello Sport': 'https://www.gazzetta.it/rss/napoli.xml',
    'Corriere dello Sport': 'https://www.corrieredellosport.it/rss/napoli',
    'TuttoSport': 'https://www.tuttosport.com/rss/calcio/napoli',
    'CalcioMercato': 'https://www.calciomercato.com/feed/rss', 
    
    # Emittenti TV/Streaming (Generici)
    'Sky Sport': 'https://sport.sky.it/rss/calcio.xml', 
    'DAZN Italia': 'https://media.dazn.com/it/news-it/rss.xml',
    'RAI Sport': 'https://www.rai.it/dl/RaiTV/rss/RaiSport_generico.xml'
}

# --- Parsing da Fonte Azzurra (Logica Invariata) ---
def parse_rss_fonteazzurra():
    """Tenta di analizzare il feed RSS di Fonte Azzurra."""
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        entries = []
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
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

# --- Scraping di Fallback SSC Napoli (Logica Invariata) ---
def scraping_fallback_sscnapoli():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers) 
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_containers = soup.select('div.elementor-posts-container article.elementor-post') or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in article_containers[:MAX_ARTICLES_PER_SOURCE]:
            a_tag = item.select_one('h3.elementor-post__title a') or item.select_one('a[href]')
            if not a_tag: continue
            
            link = a_tag['href']
            title = re.sub(r'\s+', ' ', a_tag.get_text().strip()).strip()
            
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
                'source': 'SSC Napoli (Ufficiale)' 
            }) 
        return articles
    except Exception:
        return []

# --- Aggregazione Interviste da Terze Parti (FILTRI ULTRA-RESTRITTIVI) ---
def search_third_party_interviews():
    """
    Processa i feed RSS di terze parti, filtrando per dichiarazioni/interviste esclusive dei tesserati Napoli.
    """
    interview_articles = []
    
    # Filtri per identificare dichiarazioni/interviste (più specifici)
    KEYWORD_FILTERS = ["intervista", "parole di", "dichiarazioni di", "ha detto", "ha parlato", "esclusiva", "conferenza stampa", "post-partita", "l'intervista", "la conferenza", "parole forti"]
    
    # Nomi/Titoli dei tesserati (concentrati su figure chiave per il 2025/26)
    TESSERATI_FILTERS = [
        "conte", "de laurentiis", "kvaratskhelia", "osimen", 
        "di lorenzo", "raspadori", "meret", "politano", "cajuste", 
        "mister", "presidente", "adl", "dirigente"
    ]
    
    # Feed già specifici sul Napoli
    NAPOLI_SPECIFIC_FEEDS = ['Gazzetta dello Sport', 'Corriere dello Sport', 'TuttoSport']

    for source_name, feed_url in THIRD_PARTY_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
                title_lower = title.lower()
                
                # Check 1: L'articolo ha termini di dichiarazione?
                has_interview_keywords = any(kw in title_lower for kw in KEYWORD_FILTERS)
                
                is_relevant = False
                
                if source_name in NAPOLI_SPECIFIC_FEEDS:
                    # Per i feed SPECIFICI sul Napoli, è necessario che il titolo indichi una dichiarazione E menzioni Napoli/Azzurri
                    has_napoli_or_tesserato = any(kw in title_lower for kw in ["napoli", "azzurri"] + TESSERATI_FILTERS)
                    is_relevant = has_interview_keywords and has_napoli_or_tesserato
                else:
                    # Per i feed GENERICI (Sky, DAZN, RAI, CalcioMercato), è necessario:
                    # 1. Parola chiave di dichiarazione.
                    # 2. Il nome di un Tesserato specifico (più restrittivo di prima).
                    has_tesserati_keywords = any(kw in title_lower for kw in TESSERATI_FILTERS)
                    is_relevant = has_interview_keywords and has_tesserati_keywords

                # Applica il filtro e formatta l'articolo
                if is_relevant:
                    date_str = getattr(entry, 'published', getattr(entry, 'updated', ''))
                    if date_str:
                        try:
                            date_obj = datetime(*entry.published_parsed[:6])
                            formatted_date = date_obj.strftime("%d/%m/%Y")
                        except Exception:
                            formatted_date = "Data Sconosciuta"
                    else:
                        formatted_date = "Data Sconosciuta"

                    interview_articles.append({
                        'title': title, 
                        'link': entry.link, 
                        'date': formatted_date, 
                        'source': source_name
                    })
        except Exception as e:
            print(f"Errore nel processare il feed di {source_name}: {e}")
            continue 
            
    return interview_articles

# --- Funzione Principale: Aggregazione Finale ---
def main():
    # 1. Raccolta da fonte principale
    official_articles = parse_rss_fonteazzurra()
    if not official_articles: 
        official_articles = scraping_fallback_sscnapoli()

    # 2. Raccolta da fonti terze (Interviste filtrate)
    interview_articles = search_third_party_interviews()
    
    # 3. Unione di tutte le liste
    all_articles = list(chain(official_articles, interview_articles))

    # 4. Salvataggio in feed.json
    if all_articles:
        try:
            with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_articles, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Errore durante il salvataggio di feed.json: {e}")

if __name__ == "__main__":
    main()
