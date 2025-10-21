import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
from itertools import chain
import logging

# ---------------------------
# CONFIGURAZIONE GENERALE
# ---------------------------

URL_FEED_AZZURRA = "https://www.fonteazzurra.it/feed/"
FALLBACK_URL = "https://sscnapoli.it/news/"
MAX_ARTICLES_PER_SOURCE = 100
FEED_JSON_PATH = 'feed.json'

# Limite temporale stagione 2025/26
SEASON_START = datetime(2025, 7, 1)

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# Feed di terze parti
THIRD_PARTY_FEEDS = {
    'Gazzetta dello Sport': 'https://www.gazzetta.it/rss/napoli.xml',
    'Corriere dello Sport': 'https://www.corrieredellosport.it/rss/napoli',
    'TuttoSport': 'https://www.tuttosport.com/rss/calcio/napoli',
    'CalcioMercato': 'https://www.calciomercato.com/feed/rss',
    'Sky Sport': 'https://sport.sky.it/rss/calcio.xml',
    'DAZN Italia': 'https://media.dazn.com/it/news-it/rss.xml',
    'RAI Sport': 'https://www.rai.it/dl/RaiTV/rss/RaiSport_generico.xml'
}

# ---------------------------
# PARSING FONTE AZZURRA
# ---------------------------
def parse_rss_fonteazzurra():
    logging.info("Analisi feed ufficiale Fonte Azzurra...")
    try:
        feed = feedparser.parse(URL_FEED_AZZURRA)
        entries = []

        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
            date_str = getattr(entry, 'published', getattr(entry, 'updated', ''))
            formatted_date = ""
            date_obj = None

            if date_str:
                try:
                    date_obj = datetime(*entry.published_parsed[:6])
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except Exception:
                    formatted_date = ""

            # Filtro data
            if date_obj and date_obj < SEASON_START:
                continue

            entries.append({
                'title': title,
                'link': entry.link,
                'date': formatted_date,
                'source': 'Fonte Azzurra'
            })

        logging.info(f"Fonte Azzurra: {len(entries)} articoli stagione 25/26 trovati.")
        return entries

    except Exception as e:
        logging.warning(f"Errore nel parsing Fonte Azzurra: {e}")
        return []

# ---------------------------
# SCRAPING FALLBACK SSC NAPOLI
# ---------------------------
def scraping_fallback_sscnapoli():
    logging.info("Avvio scraping fallback SSC Napoli...")
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FALLBACK_URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        containers = soup.select('div.elementor-posts-container article.elementor-post') \
                     or soup.find_all('div', class_=re.compile(r'elementor-post__card|post-card'))

        for item in containers[:MAX_ARTICLES_PER_SOURCE]:
            a_tag = item.select_one('h3.elementor-post__title a') or item.select_one('a[href]')
            if not a_tag:
                continue

            link = a_tag['href']
            title = re.sub(r'\s+', ' ', a_tag.get_text().strip())
            title_parts = title.split()
            mid = len(title_parts) // 2
            if ' '.join(title_parts[:mid]) == ' '.join(title_parts[mid:]):
                title = ' '.join(title_parts[:mid])
            if not title:
                title = "Senza titolo"

            date_tag = item.select_one('div.elementor-post__meta-data span.elementor-post-date')
            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', date_tag.get_text().strip()) if date_tag else None
            formatted_date = date_match.group(0) if date_match else ""
            date_obj = None

            if date_match:
                try:
                    date_obj = datetime.strptime(formatted_date, "%d/%m/%Y")
                except ValueError:
                    pass

            # Filtro data
            if date_obj and date_obj < SEASON_START:
                continue

            articles.append({
                'title': title,
                'link': link,
                'date': formatted_date,
                'source': 'SSC Napoli (Ufficiale)'
            })

        logging.info(f"SSC Napoli fallback: {len(articles)} articoli stagione 25/26 trovati.")
        return articles

    except Exception as e:
        logging.warning(f"Errore scraping fallback SSC Napoli: {e}")
        return []

# ---------------------------
# INTERVISTE TERZE PARTI (STAGIONE 25/26)
# ---------------------------
def search_third_party_interviews():
    logging.info("Analisi testate esterne per interviste stagione 25/26...")
    interview_articles = []

    KEYWORD_FILTERS = [
        "dice", "ha detto", "parole di", "intervista a", "conferenza",
        "post-partita", "la replica", "ha rilasciato", "la verità di",
        "esclusiva", "parla di"
    ]

    TESSERATI_FILTERS = [
        "conte", "de laurentiis", "manna", "adl", "presidente", "ds", "allenatore",
        "meret", "milinković-savić", "contini",
        "buongiorno", "beukema", "rrahmani", "marianucci", "juan jesus",
        "miguel gutiérrez", "olivera", "spinazzola", "di lorenzo", "mazzocchi",
        "lobotka", "gilmour", "mctominay", "anguissa", "de bruyne",
        "elmas", "vergara", "lang",
        "david neres", "politano", "højlund", "lucca", "lukaku", "ambrosino"
    ]

    EXCLUSION_FILTERS = [
        "secondo", "pista", "cessione", "mercato", "rumors", "affare", "trattativa",
        "ipotesi", "obiettivo", "valutazione", "moglie", "agente", "ex", "idea di",
        "il punto", "infortunio", "le cifre", "eredi", "retroscena", "accostato",
        "proposta", "chiama", "l'ombra", "possibile"
    ]

    NAPOLI_SPECIFIC_FEEDS = ['Gazzetta dello Sport', 'Corriere dello Sport', 'TuttoSport']

    for source_name, feed_url in THIRD_PARTY_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            logging.info(f"Analisi feed {source_name}... ({len(feed.entries)} articoli)")

            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                title = BeautifulSoup(entry.title, 'html.parser').get_text().strip()
                title_lower = title.lower()

                if any(ex in title_lower for ex in EXCLUSION_FILTERS):
                    continue
                if not any(kw in title_lower for kw in KEYWORD_FILTERS):
                    continue

                if source_name in NAPOLI_SPECIFIC_FEEDS:
                    relevant = any(kw in title_lower for kw in ["napoli", "azzurri"] + TESSERATI_FILTERS)
                else:
                    relevant = any(kw in title_lower for kw in TESSERATI_FILTERS)

                if not relevant:
                    continue

                date_str = getattr(entry, 'published', getattr(entry, 'updated', ''))
                date_obj = None
                formatted_date = "Data Sconosciuta"

                if date_str:
                    try:
                        date_obj = datetime(*entry.published_parsed[:6])
                        formatted_date = date_obj.strftime("%d/%m/%Y")
                    except Exception:
                        pass

                # Filtro temporale
                if date_obj and date_obj < SEASON_START:
                    continue

                interview_articles.append({
                    'title': title,
                    'link': entry.link,
                    'date': formatted_date,
                    'source': source_name
                })

        except Exception as e:
            logging.warning(f"Errore nel feed di {source_name}: {e}")
            continue

    logging.info(f"Totale interviste valide stagione 25/26: {len(interview_articles)}")
    return interview_articles

# ---------------------------
# FUNZIONE PRINCIPALE
# ---------------------------
def main():
    logging.info("========== AVVIO AGGREGATORE STAGIONE 25/26 ==========")

    official_articles = parse_rss_fonteazzurra()
    if not official_articles:
        logging.warning("Nessun articolo da Fonte Azzurra. Attivo fallback SSC Napoli...")
        official_articles = scraping_fallback_sscnapoli()

    interview_articles = search_third_party_interviews()

    all_articles = list(chain(official_articles, interview_articles))

    if all_articles:
        try:
            with open(FEED_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_articles, f, indent=4, ensure_ascii=False)
            logging.info(f"Salvato {len(all_articles)} articoli stagione 25/26 in '{FEED_JSON_PATH}'.")
        except Exception as e:
            logging.error(f"Errore durante il salvataggio di feed.json: {e}")
    else:
        logging.warning("Nessun articolo trovato per la stagione 25/26.")

    logging.info("========== AGGREGAZIONE COMPLETATA ==========")

# ---------------------------
# ESECUZIONE SCRIPT
# ---------------------------
if __name__ == "__main__":
    main()
