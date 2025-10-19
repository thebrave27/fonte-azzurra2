def scraping_fallback():
    """Esegue lo scraping degli articoli dal sito SSC Napoli (fallback)."""
    print(f"🧩 Fallback attivo: estraggo articoli dal sito SSC Napoli da {FALLBACK_URL}...")
    articles = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(FALLBACK_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Selettore ESATTO per i container degli articoli sulla pagina /news/
        # Usiamo il selettore che contiene sia l'immagine che il titolo/data
        article_containers = soup.select('div.elementor-posts-container article.elementor-post')
        
        if not article_containers:
            print("❌ Errore nello scraping: Nessun contenitore articolo trovato con selettore specifico.")
            return articles


        for item in article_containers[:MAX_ARTICLES]:
            
            # 1. Estrazione Link
            # Il link è contenuto in un <a> che a sua volta contiene il titolo
            a_tag = item.select_one('h3.elementor-post__title a')
            if not a_tag:
                # Fallback: cerca un <a> generico nell'articolo
                a_tag = item.select_one('a[href]')
                if not a_tag:
                    continue
            
            link = a_tag['href']
            
            # 2. Estrazione Titolo (più robusta)
            title = a_tag.get_text().strip()
            title = re.sub(r'\s+', ' ', title).strip()
            
            if not title or title.lower() in ['leggi tutto', 'read more', 'senza titolo']:
                 # Cerco un tag titolo specifico se fallisce l'estrazione da <a>
                 title_tag = item.select_one('h3.elementor-post__title')
                 if title_tag:
                     title = title_tag.get_text().strip()
                 else:
                     title = "Senza titolo (Fallback di emergenza)"


            # 3. Estrazione Data (Selettore più specifico)
            # La data è contenuta in un <span> all'interno di un <div> meta data
            date_tag = item.select_one('div.elementor-post__meta-data span.elementor-post-date')
            date_str = date_tag.get_text().strip() if date_tag else ""
            
            # Estrazione del formato data gg/mm/aaaa
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
