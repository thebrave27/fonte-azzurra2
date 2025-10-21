import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
from itertools import chain

# --- CONFIGURAZIONE GLOBALE ---

# URL delle fonti
URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/" 

# Feed di Terze Parti
THIRD_PARTY_FEEDS = {
    'Gazzetta dello Sport': 'https://www.gazzetta.it/rss/napoli.xml',
    'Corriere dello Sport': 'https://www.corrieredellosport.it/rss/napoli',
    'TuttoSport': 'https://www.tuttosport.com/rss/calcio/napoli',
    'CalcioMercato': 'https://www.calciomercato.com/feed/rss', 
    'Sky Sport': 'https://sport.sky.it/rss/calcio.xml', 
    'DAZN Italia': 'https://media.dazn.com/it/news-it/rss.xml',
    'RAI Sport': 'https://www.rai.it/dl/RaiTV/rss/RaiSport_generico.xml'
}

# Impostazioni
MAX_ARTICLES_PER_SOURCE = 100 
FEED_JSON_PATH = 'feed.json'
# Filtro Temporale: Inizio stagione per filtrare gli articoli vecchi (1 Luglio 2025)
SEASON_START = datetime(2025, 7, 1)

# --- FILTRI CHIAVE (ROSA 25/26) ---

# Tesserati/Persone da monitorare (Dirigenza, Tecnici, Giocatori)
TESSERATI_FILTERS = [
    "conte", "de laurentiis", "manna", "adl", "presidente", "ds", "allenatore", 
    "meret", "milinković-savić", "contini", "buongiorno", "beukema", 
    "rrahmani", "marianucci", "juan jesus", "miguel gutiérrez", "olivera", 
    "spinazzola", "di lorenzo", "mazzocchi", "lobotka", "gilmour", 
    "mctominay", "anguissa", "de bruyne", "elmas", "vergara", "lang", 
    "david neres", "politano", "højlund", "lucca", "lukaku", "ambrosino"
]
# Parole chiave per intercettare dichiarazioni dirette/ufficiali
KEYWORD_FILTERS = ["dice", "ha detto", "parole di", "intervista a", "conferenza", "post-partita", "la replica", "ha rilasciato", "la verità di", "esclusiva", "parla di"]
# Parole chiave da escludere (tipiche del calciomercato o voci)
EXCLUSION_FILTERS = ["secondo", "pista", "cessione", "mercato", "rumors", "affare", "trattativa", "ipotesi", "obiettivo", "valutazione", "moglie", "agente", "ex", "il punto", "infortunio", "le cifre", "eredi", "retroscena", "accostato", "proposta", "chiama", "l'ombra", "possibile"]
# Feed specifici che non necessitano del filtro sul nome del giocatore, ma solo del club
NAPOLI_SPECIFIC_FEEDS = ['Gazzetta dello Sport', 'Corriere dello Sport', 'TuttoSport']


# ---------------------------
# UTILITY PER DATA E FILTRI
# ---------------------------

def _extract_rss_date(entry):
    """Estrae, parse la data RSS e applica il filtro temporale."""
    date_str = getattr(entry, 'published', getattr(entry, 'updated', ''))
    if date_str:
        try:
            # Crea l'oggetto datetime basato sul parsing di feedparser
            date_obj = datetime(*entry.published_parsed[:6]) 
            if date_obj >= SEASON_START:
                return date_obj, date_obj.strftime("%d/%m/%Y")
        except Exception:
            pass # Data non valida o mancante
    return None, "Data Sconosciuta"

def _extract_scraping_date(date_str):
    """Estrae, parse la data DD/MM/YYYY e applica il filtro temporale."""
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            if date_obj >= SEASON_START:
                return date_obj, date_str
        except ValueError:
            pass # Data non valida
    return None, "Data Sconosciuta"

# ---------------------------
# FUNZIONI DI PARSING
# ---------------------------

def parse_rss_fonteazzurra():
    """Analizza il feed RSS principale."""
    entries = []
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            # Pulisce il titolo da eventuali tag HTML
            title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
            
            date_obj, formatted_date = _extract_rss_date(entry)
            if date_obj is None: 
                continue # Scartato dal filtro data

            entries.append({
                'title': title, 
                'link': entry.link, 
                'date': formatted_date, 
                'date_obj': date_obj, # Aggiungo l'oggetto data per l'ordinamento finale
                'source': 'Fonte Azzurra'
            })
        return entries
    except Exception:
        return []

def scraping_fallback_sscnapoli():
    """Esegue lo scraping come fallback per il sito ufficiale SSC Napoli."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # Tenta di trovare i container comuni degli articoli
        containers = soup.select('div.elementor-posts-container article.elementor-post') \
                     or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in containers[:MAX_ARTICLES_PER_SOURCE]:
            a_tag = item.select_one('h3.elementor-post__title a') or item.select_one('a[href]')
            if not a_tag: continue
            
            link = a_tag['href']
            # Pulisce spazi multipli e titoli generici
            title = re.sub(r'\s+', ' ', a_tag.get_text().strip())
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                title = "Senza titolo"

            # Estrazione data
            date_tag = item.select_one('div.elementor-post__meta-data span.elementor-post-date')
            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_tag.get_text().strip()) if date_tag else None
            
            date_obj, formatted_date = _extract_scraping_date(date_match.group(0) if date_match else None)
            if date_obj is None: 
                continue # Scartato dal filtro data

            articles.append({
                'title': title, 
                'link': link, 
                'date': formatted_date, 
                'date_obj': date_obj,
                'source': 'SSC Napoli (Ufficiale - Scraping)' 
            }) 
        return articles
    except requests.RequestException:
        return []
    except Exception:
        return []

def search_third_party_interviews():
    """Processa i feed RSS di terze parti con filtri specifici per interviste/dichiarazioni."""
    interview_articles = []
    
    for source_name, feed_url in THIRD_PARTY_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
                title_lower = title.lower()

                # 1. Filtro Esclusione/Parole chiave Dichiarazioni
                if any(ex in title_lower for ex in EXCLUSION_FILTERS):
                    continue
                if not any(kw in title_lower for kw in KEYWORD_FILTERS):
                    continue

                # 2. Controllo Rilevanza Tesserati
                if source_name in NAPOLI_SPECIFIC_FEEDS:
                    # Nei feed Napoli-specifici, basta che contenga Napoli o un tesserato
                    relevant = any(kw in title_lower for kw in ["napoli", "azzurri"] + TESSERATI_FILTERS)
                else:
                    # Nei feed generici, deve menzionare un tesserato
                    relevant = any(kw in title_lower for kw in TESSERATI_FILTERS)

                if not relevant:
                    continue

                # 3. Controllo Data e Filtro Temporale
                date_obj, formatted_date = _extract_rss_date(entry)
                if date_obj is None: 
                    continue

                interview_articles.append({
                    'title': title, 
                    'link': entry.link, 
                    'date': formatted_date, 
                    'date_obj': date_obj,
                    'source': source_name
                })
        except Exception:
            continue # Passa al prossimo feed in caso di errore
            
    return interview_articles

# ---------------------------
# FUNZIONE PRINCIPALE
# ---------------------------
def main():
    """Esegue l'aggregazione, l'ordinamento e il salvataggio."""
    
    # 1. Raccolta Articoli
    official_articles = parse_rss_fonteazzurra()
    if not official_articles: 
        official_articles = scraping_fallback_sscnapoli()

    interview_articles = search_third_party_interviews()
    
    all_articles = list(chain(official_articles, interview_articles))
    
    if not all_articles:
        # Se non ci sono articoli, potremmo voler terminare o lasciare un file vuoto
        # Ma per sicurezza, usciamo qui se non abbiamo dati.
        return

    # 2. Ordinamento
    # Ordina tutti gli articoli (dal più recente al più datato) usando 'date_obj'
    # Fallback all'ordinamento per titolo in caso di data mancante (non dovrebbe accadere)
    all_articles.sort(key=lambda x: x.get('date_obj', datetime.min), reverse=True)
    
    # 3. Pulizia e Salvataggio
    # Rimuove l'oggetto 'date_obj' prima di salvare in JSON per pulizia
    for article in all_articles:
        if 'date_obj' in article:
            del article['date_obj']

    try:
        with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, indent=4, ensure_ascii=False)
    except Exception as e:
        # In un ambiente di automazione, questo errore dovrebbe essere registrato
        pass

if __name__ == "__main__":
    main()
