# -*- coding: utf-8 -*-
# Na početku parser.py dodaj:
try:
    from .subtitles import (
        parse_subtitles_basic,
        parse_subtitles_advanced,
        download_subtitle
    )
except ImportError:
    # Kreiraj placeholder funkcije ako subtitles.py ne postoji
    def parse_subtitles_basic(*args, **kwargs):
        print("WARNING: Subtitles module not loaded")
        return []
    
    def parse_subtitles_advanced(*args, **kwargs):
        print("WARNING: Subtitles module not loaded")
        return []
    
    def download_subtitle(*args, **kwargs):
        return None
import os
import re
import time
import requests
import urllib.request
import gzip
import io
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

CACHE_DIR = "/tmp/Titlovi_Browser"
POPULAR_URL = "https://rs.titlovi.com/?v=1"
CACHE_FILE = os.path.join(CACHE_DIR, "popular.html")
CACHE_TTL = 60 * 30  # 30 minuta


def ensure_cache():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def download(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "sr-RS,sr;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    )
    
    with urllib.request.urlopen(req, timeout=15) as r:
        # Pročitaj sadržaj
        content = r.read()
        
        # Provjeri da li je odgovor gzip kompresovan
        if r.headers.get('Content-Encoding') == 'gzip':
            # Dekompresuj gzip
            try:
                content = gzip.decompress(content)
            except:
                # Ako ne uspe dekompresija, pokušaj drugi način
                try:
                    with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                        content = f.read()
                except:
                    pass  # Ostavi originalni sadržaj
        
        # Pokušaj dekodirati
        try:
            return content.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            # Ako UTF-8 ne radi, pokušaj druge enkodinge
            try:
                return content.decode('iso-8859-1', errors='ignore')
            except:
                return content.decode('ascii', errors='ignore')


def get_cached_or_download(url, cache_file):
    ensure_cache()

    if os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < CACHE_TTL:
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()

    html = download(url)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(html)
    return html


# parser.py - dodaj ove funkcije

def parse_popular_movies():
    """Parsira samo popularne filmove"""
    html = get_cached_or_download(POPULAR_URL, CACHE_FILE)
    return parse_list_by_title(html, "Popularni filmovi")


def parse_popular_series():
    """Parsira samo popularne serije"""
    html = get_cached_or_download(POPULAR_URL, CACHE_FILE)
    return parse_list_by_title(html, "Popularne serije")


def parse_new_movies():
    """Parsira samo nove filmove"""
    html = get_cached_or_download(POPULAR_URL, CACHE_FILE)
    return parse_list_by_title(html, "Novi filmovi")


def parse_list_by_title(html, title_text):
    """Pomoćna funkcija koja parsira određenu listu po naslovu"""
    results = []

    # Pronađi sekciju sa datim naslovom
    # Tražimo pattern: <h2>Naslov</h2>... pa lista
    import re

    # Kreiraj regex pattern za određeni naslov
    pattern = f'<h2>{re.escape(title_text)}</h2>(.*?)</div>'
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)

    if not match:
        print(f"DEBUG: Nije pronađena sekcija '{title_text}'")
        return results

    section = match.group(1)
    print(f"DEBUG: Pronađena sekcija '{title_text}' ({len(section)} chars)")

    # Sada parsiraj sve linkove u ovoj sekciji
    # Pattern za filmove/serije: <a href="/filmovi/..."> ili <a href="/serije/...">
    link_pattern = r'<a\s+href="(/[^"]+)"[^>]*>([^<]+)</a>'
    links = re.findall(link_pattern, section, re.IGNORECASE)

    seen = set()
    for href, title in links:
        title = title.strip()
        if len(title) < 2 or title in seen:
            continue

        # Filtriraj samo filmove/serije (isključi slike i druge linkove)
        if not ('/filmovi/' in href or '/serije/' in href):
            continue

        seen.add(title)

        # Popuni puni URL
        if href.startswith('/'):
            url = "https://rs.titlovi.com" + href
        else:
            url = href

        # Ekstraktuj ID
        movie_id = None
        parts = href.split('/')
        for part in parts:
            if part.isdigit() and len(part) > 3:
                movie_id = part
                break

        results.append({
            "title": title,
            "url": url,
            "id": movie_id,
            "type": "serije" if "/serije/" in href else "filmovi"
        })

    print(f"DEBUG: Pronađeno {len(results)} stavki za '{title_text}'")
    return results


# parser.py - dodaj ove funkcije
# ... (ostali importi i postojeći kod ostaju isti)

def parse_all_movies(max_results=60, sort_by=4):
    """
    Parsira filmove sa više stranica do max_results (bez paginacije, samo lista).
    """
    print(f"DEBUG: parse_all_movies pozvan - max_results={max_results}")

    try:
        results = []
        current_page = 1
        max_pages = 5  # Ograničenje da ne učitavamo previše (5 stranica ~60 rezultata)
        seen_titles = set()  # Da izbegnemo duplikate

        while len(results) < max_results and current_page <= max_pages:
            # Kreiraj URL sa paginacijom i sortiranjem
            url = f"https://rs.titlovi.com/filmovi/?pg={current_page}&sort={sort_by}"
            html = download(url)

            print(f"DEBUG: HTML dužina za stranu {current_page}: {len(html)}")

            # JEDNOSTAVNI REGEX za pronalaženje filmova
            movie_pattern = r'<a\s+href="(/filmovi/[^"]+/)"[^>]*>([^<]+)</a>'
            matches = re.findall(movie_pattern, html, re.IGNORECASE)

            print(f"DEBUG: Pronađeno {len(matches)} potencijalnih filmova na strani {current_page}")

            for href, title in matches:
                title = re.sub(r'\s+', ' ', title).strip()

                if not title or len(title) < 2 or title in seen_titles:
                    continue

                seen_titles.add(title)

                # Proveri da li je naslov previše generičan
                if title.lower() in ['filmovi', 'serije', 'pretraga', 'login', 'registruj se']:
                    continue

                # Popuni puni URL
                url_full = "https://rs.titlovi.com" + href

                # Ekstraktuj ID
                movie_id = None
                parts = href.split('/')
                for part in parts:
                    if part.isdigit() and len(part) > 3:
                        movie_id = part
                        break

                results.append({
                    "title": title,
                    "url": url_full,
                    "id": movie_id,
                    "year": "N/A",
                    "genres": "N/A",
                    "type": "film"
                })

                # Prekini ako smo dostigli max_results
                if len(results) >= max_results:
                    break

            # Idi na sledeću stranicu
            current_page += 1

        print(f"DEBUG: Vraćam {len(results)} filmova (ukupno učitano {current_page-1} stranica)")

        # Ako nema rezultata, vrati test podatke
        if not results:
            print("DEBUG: Nema rezultata, vraćam test podatke")
            results = [
                {
                    "title": "Test Film 1",
                    "url": "https://rs.titlovi.com/filmovi/test-1/",
                    "id": "12345",
                    "year": "2023",
                    "genres": "Akcija",
                    "type": "film"
                },
                # ... (dodaj više ako treba)
            ]

        return {
            "items": results,
            "current_page": 1,  # Bez paginacije, uvek 1
            "has_next": False,
            "has_prev": False,
            "total_pages": 1,
            "total_items": len(results)
        }

    except Exception as e:
        print(f"Greška u parse_all_movies: {e}")
        import traceback
        traceback.print_exc()
        return {
            "items": [],
            "current_page": 1,
            "has_next": False,
            "has_prev": False,
            "total_pages": 1,
            "total_items": 0
        }

def parse_all_series(max_results=60, sort_by=4):
    """Parsira punu listu svih serija sa više stranica do max_results (bez paginacije)."""
    results = []
    current_page = 1
    max_pages = 5  # Ograničenje (5 stranica ~60 rezultata)
    seen_titles = set()

    while len(results) < max_results and current_page <= max_pages:
        base_url = "https://rs.titlovi.com/serije/"
        params = {}
        if current_page > 1:
            params['pg'] = current_page
        if sort_by != 4:
            params['sort'] = sort_by

        url = base_url
        if params:
            url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

        print(f"DEBUG: Parsiram serije sa URL: {url}")

        try:
            html = download(url)
            print(f"DEBUG: HTML dužina za serije (strana {current_page}): {len(html)}")

            soup = BeautifulSoup(html, 'html.parser')

            # Pronađi sekciju sa serijama
            section = soup.find('section', class_='movies')
            if not section:
                print(f"DEBUG: Nije pronađena sekcija serija na strani {current_page}")
                break

            # Pronađi sve li elemente u ul.serije
            series_list = section.find('ul', class_='serije')
            if series_list:
                series_items = series_list.find_all('li')

                for item in series_items:
                    try:
                        # Naslov
                        title_tag = item.find('h3').find('a')
                        title = title_tag.get_text(strip=True) if title_tag else "N/A"

                        if not title or title in seen_titles:
                            continue

                        seen_titles.add(title)

                        # Godina (obično u <i> tagu unutar <h3>)
                        year_tag = item.find('h3').find('i')
                        year = year_tag.get_text(strip=True).strip('()') if year_tag else "N/A"

                        # Žanrovi (u <h4>)
                        genres_tag = item.find('h4')
                        genres = genres_tag.get_text(strip=True, separator=", ") if genres_tag else "N/A"

                        # Opis (u <h5>)
                        plot_tag = item.find('h5')
                        plot = plot_tag.get_text(strip=True) if plot_tag else "N/A"

                        # Slika (cover)
                        image_tag = item.find('img')
                        image_url = image_tag['src'] if image_tag else ""

                        # Link do stranice serije
                        link_tag = item.find('a')
                        href = link_tag['href'] if link_tag and 'href' in link_tag.attrs else ""
                        full_url = "https://rs.titlovi.com" + href if href.startswith('/') else href

                        # Ekstraktuj ID
                        series_id = None
                        if href:
                            parts = href.split('/')
                            for part in parts:
                                if part.isdigit() and len(part) > 3:
                                    series_id = part
                                    break

                        # Dodaj u rezultate
                        results.append({
                            "title": title,
                            "url": full_url,
                            "id": series_id,
                            "year": year,
                            "genres": genres,
                            "plot": plot,
                            "image_url": image_url,
                            "type": "series"
                        })

                        if len(results) >= max_results:
                            break

                    except Exception as e:
                        print(f"DEBUG: Greška pri parsiranju serije: {e}")
                        continue

            # Idi na sledeću stranicu
            current_page += 1

        except Exception as e:
            print(f"Greška u parse_all_series na strani {current_page}: {e}")
            import traceback
            traceback.print_exc()
            break

    print(f"DEBUG: Pronađeno {len(results)} serija (ukupno učitano {current_page-1} stranica)")

    return {
        "items": results,
        "current_page": 1,  # Bez paginacije
        "has_next": False,
        "has_prev": False,
        "total_pages": 1,
        "total_items": len(results)
    }

def parse_series_details(url, html_content=None):
    """Parsira detalje serije (slično kao za filmove)"""
    try:
        # Ako je dat HTML sadržaj, koristi ga
        if html_content:
            print(f"DEBUG: Parsiram seriju iz HTML sadržaja")
            content = html_content
            # Sačuvaj u cache
            cache_file = os.path.join(CACHE_DIR, f"series_{hash(url)}.html")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Ako nema HTML, preuzmi sa URL-a
            print(f"DEBUG: Preuzimam HTML za seriju: {url}")
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/115.0'
            }, timeout=10)

            if response.status_code != 200:
                print(f"DEBUG: HTTP greška: {response.status_code}")
                return None

            content = response.text

            # Sačuvaj u cache
            cache_file = os.path.join(CACHE_DIR, f"series_{hash(url)}.html")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)

        # Sada parsiraj HTML
        soup = BeautifulSoup(content, 'html.parser')
        details = {}

        # 1. NASLOV
        title_elem = soup.find('h1', itemprop='name')
        details['title'] = title_elem.get_text(strip=True) if title_elem else "N/A"
        print(f"DEBUG: Naslov serije: {details['title']}")

        # 2. OPIS
        description_elem = soup.find('span', itemprop='description')
        if description_elem:
            plot_text = description_elem.get_text(separator='\n', strip=True)
            plot_text = plot_text.replace('\n\n', '\n')
            if plot_text.endswith('[Index]'):
                plot_text = plot_text[:-7].strip()
            details['plot'] = plot_text
            print(f"DEBUG: Opis pronađen, dužina: {len(plot_text)}")
        else:
            print("DEBUG: Opis nije pronađen")
            details['plot'] = "Opis nije dostupan"

        # 3. GODINA
        year_match = re.search(r'\((\d{4})\)', content)
        details['year'] = year_match.group(1) if year_match else "N/A"
        print(f"DEBUG: Godina: {details['year']}")

        # 4. ŽANR
        genre_elem = soup.find('h3')
        if genre_elem:
            genre_text = genre_elem.get_text(strip=True)
            if '(' in genre_text:
                genre_text = genre_text.split('(')[0].strip()
            details['genre'] = genre_text
            print(f"DEBUG: Žanr: {details['genre']}")
        else:
            details['genre'] = "N/A"

        # 5. TRAJANJE EPIZODE
        duration_match = re.search(r'<h4>Trajanje:</h4>\s*(.*?)</br>', content, re.DOTALL)
        if duration_match:
            details['duration'] = duration_match.group(1).strip()
            print(f"DEBUG: Trajanje epizode: {details['duration']}")
        else:
            details['duration'] = "N/A"

        # 6. SEZONE
        seasons_match = re.search(r'<h4>Sezone:</h4>\s*(.*?)</br>', content, re.DOTALL)
        if seasons_match:
            details['seasons'] = seasons_match.group(1).strip()
        else:
            details['seasons'] = "N/A"

        # 7. EPIZODE
        episodes_match = re.search(r'<h4>Epizode:</h4>\s*(.*?)</br>', content, re.DOTALL)
        if episodes_match:
            details['episodes'] = episodes_match.group(1).strip()
        else:
            details['episodes'] = "N/A"

        # 8. TV KANAL
        channel_match = re.search(r'<h4>TV kanal:</h4>\s*(.*?)</br>', content, re.DOTALL)
        if channel_match:
            details['channel'] = channel_match.group(1).strip()
        else:
            details['channel'] = "N/A"

        # 9. REŽIJA
        director_match = re.search(r'<h4>Režija:</h4>(.*?)</br>', content, re.DOTALL)
        if director_match:
            director_text = director_match.group(1).strip()
            soup2 = BeautifulSoup(director_text, 'html.parser')
            details['director'] = soup2.get_text(strip=True)
            print(f"DEBUG: Režija: {details['director']}")
        else:
            details['director'] = "N/A"

        # 10. SCENARIO
        writer_match = re.search(r'<h4>Scenario:</h4>(.*?)</br>', content, re.DOTALL)
        if writer_match:
            writer_text = writer_match.group(1).strip()
            soup2 = BeautifulSoup(writer_text, 'html.parser')
            details['writer'] = soup2.get_text(strip=True)
            print(f"DEBUG: Scenario: {details['writer']}")
        else:
            details['writer'] = "N/A"

        # 11. GLAVNE ULOGE
        cast_start = content.find('<h4>Glavne uloge:</h4>')
        if cast_start != -1:
            cast_end = content.find('</br></div>', cast_start)
            if cast_end != -1:
                cast_html = content[cast_start:cast_end]
                soup2 = BeautifulSoup(cast_html, 'html.parser')
                actor_links = soup2.find_all('a', class_='moviePersonPopup')
                actors = []
                for link in actor_links:
                    span = link.find('span', itemprop='name')
                    if span:
                        actors.append(span.get_text(strip=True))
                details['cast'] = ', '.join(actors) if actors else "N/A"
                print(f"DEBUG: Glumci ({len(actors)}): {', '.join(actors[:3])}...")
            else:
                details['cast'] = "N/A"
        else:
            details['cast'] = "N/A"

        # 12. IMDb
        imdb_elem = soup.find('a', class_='imdb')
        details['imdb'] = "IMDb link" if imdb_elem else "N/A"

        # 13. POSTER URL
        poster_elem = soup.find('img', class_='cover', itemprop='image')
        if poster_elem:
            details['poster_url'] = poster_elem.get('src', '')
            print(f"DEBUG: Poster URL: {details['poster_url']}")
        else:
            details['poster_url'] = ''

        # 14. TIP (serija)
        details['type'] = 'series'

        print(f"DEBUG: Parsiranje serije završeno")
        return details

    except Exception as e:
        print(f"Greška pri parsiranju detalja serije: {e}")
        import traceback
        traceback.print_exc()
        return None


def search_series(query):
    """Pretražuje serije po upitu"""
    if not query or len(query.strip()) < 2:
        return []

    search_url = f"https://rs.titlovi.com/serije/?q={quote_plus(query)}"

    try:
        html = download(search_url)

        print(f"DEBUG search_series: Pretraga serija za '{query}'")
        print(f"DEBUG: HTML dužina: {len(html)}")

        results = []
        seen_titles = set()

        # Parsiraj serije na isti način kao parse_all_series
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.find('section', class_='movies')

        if section:
            series_list = section.find('ul', class_='serije')
            if series_list:
                series_items = series_list.find_all('li')

                for item in series_items:
                    try:
                        title_tag = item.find('h3').find('a')
                        title = title_tag.get_text(strip=True) if title_tag else "N/A"

                        if not title or title in seen_titles:
                            continue

                        seen_titles.add(title)

                        # Link
                        link_tag = item.find('a')
                        href = link_tag['href'] if link_tag and 'href' in link_tag.attrs else ""
                        full_url = "https://rs.titlovi.com" + href if href.startswith('/') else href

                        # Godina
                        year_tag = item.find('h3').find('i')
                        year = year_tag.get_text(strip=True).strip('()') if year_tag else "N/A"

                        # ID
                        series_id = None
                        if href:
                            parts = href.split('/')
                            for part in parts:
                                if part.isdigit() and len(part) > 3:
                                    series_id = part
                                    break

                        results.append({
                            "title": title,
                            "url": full_url,
                            "id": series_id,
                            "year": year,
                            "type": "series"
                        })

                        if len(results) >= 25:
                            break

                    except Exception as e:
                        print(f"DEBUG: Greška pri parsiranju serije u pretrazi: {e}")
                        continue

        print(f"DEBUG search_series: Pronađeno {len(results)} serija")
        return results

    except Exception as e:
        print(f"Greška u search_series: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_boxoffice_srbija():
    """Parsira najgledanije filmove u Srbiji"""
    url = "https://rs.titlovi.com/clanci/10986/najgledaniji-filmovi-u-srbiji/"
    html = download(url)
    return parse_boxoffice_table(html, "Box Office - Srbija")


def parse_boxoffice_hrvatska():
    """Parsira najgledanije filmove u Hrvatskoj"""
    url = "https://rs.titlovi.com/clanci/10985/najgledaniji-filmovi-u-hrvatskoj/"
    html = download(url)
    return parse_boxoffice_table(html, "Box Office - Hrvatska")


def parse_boxoffice_sad():
    """Parsira najgledanije filmove u SAD"""
    url = "https://rs.titlovi.com/clanci/10988/najgledaniji-filmovi-u-sad/"
    html = download(url)
    return parse_boxoffice_table(html, "Box Office - SAD")


def parse_boxoffice_table(html, title):
    """Pomoćna funkcija koja parsira tabelu sa Box Office podacima"""
    results = []

    print(f"DEBUG: Parsiranje Box Office tabele za {title}")

    # Pattern za pronalaženje tabele sa filmovima
    # Tražimo redove u tabeli koji sadrže linkove na filmove
    table_pattern = r'<table[^>]*>.*?</table>'
    table_match = re.search(table_pattern, html, re.DOTALL | re.IGNORECASE)

    if not table_match:
        print(f"DEBUG: Nije pronađena tabela za {title}")
        return results

    table_html = table_match.group(0)

    # Pronađi sve redove u tabeli koji sadrže linkove na filmove
    # Format: <td><a href="https://titlovi.com/filmovi/...">Naziv filma</a></td>
    movie_pattern = r'<a\s+href="(https://titlovi\.com/filmovi/[^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(movie_pattern, table_html, re.IGNORECASE)

    seen = set()
    for href, movie_title in matches:
        movie_title = movie_title.strip()

        if not movie_title or movie_title in seen:
            continue

        seen.add(movie_title)

        # Proveri da li link vodi na filmove (sadrži /filmovi/)
        if '/filmovi/' not in href:
            continue

        # Ekstraktuj ID iz URL-a
        movie_id = None
        parts = href.split('/')
        for part in parts:
            if part.isdigit() and len(part) > 3:
                movie_id = part
                break

        # Konvertuj titlovi.com link u rs.titlovi.com
        url = href.replace('https://titlovi.com/', 'https://rs.titlovi.com/')

        results.append({
            "title": movie_title,
            "url": url,
            "id": movie_id,
            "type": "film",
            "source": title
        })

    print(f"DEBUG: Pronađeno {len(results)} filmova za {title}")
    return results
# parser.py
def parse_movie_details(url, html_content=None):
    """Parsira detalje filma. Može primiti URL ili HTML sadržaj."""
    try:
        # Ako je dat HTML sadržaj, koristi ga
        if html_content:
            print(f"DEBUG: Parsiram iz HTML sadržaja")
            content = html_content
            # Sačuvaj u cache
            cache_file = os.path.join(CACHE_DIR, f"movie_{hash(url)}.html")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Ako nema HTML, preuzmi sa URL-a
            print(f"DEBUG: Preuzimam HTML sa URL: {url}")
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/115.0'
            }, timeout=10)

            if response.status_code != 200:
                print(f"DEBUG: HTTP greška: {response.status_code}")
                return None

            content = response.text

            # Sačuvaj u cache
            cache_file = os.path.join(CACHE_DIR, f"movie_{hash(url)}.html")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)

        # Sada parsiraj HTML
        soup = BeautifulSoup(content, 'html.parser')
        details = {}

        # 1. NASLOV
        title_elem = soup.find('h1', itemprop='name')
        details['title'] = title_elem.get_text(strip=True) if title_elem else "N/A"
        print(f"DEBUG: Naslov: {details['title']}")

        # 2. OPIS
        description_elem = soup.find('span', itemprop='description')
        if description_elem:
            plot_text = description_elem.get_text(separator='\n', strip=True)
            plot_text = plot_text.replace('\n\n', '\n')
            if plot_text.endswith('[Index]'):
                plot_text = plot_text[:-7].strip()
            details['plot'] = plot_text
            print(f"DEBUG: Opis pronađen, dužina: {len(plot_text)}")
        else:
            print("DEBUG: Opis nije pronađen")
            details['plot'] = "Opis nije dostupan"

        # 3. GODINA
        year_match = re.search(r'\((\d{4})\)', content)
        details['year'] = year_match.group(1) if year_match else "N/A"
        print(f"DEBUG: Godina: {details['year']}")

        # 4. ŽANR
        genre_elem = soup.find('h3')
        if genre_elem:
            genre_text = genre_elem.get_text(strip=True)
            if '(' in genre_text:
                genre_text = genre_text.split('(')[0].strip()
            details['genre'] = genre_text
            print(f"DEBUG: Žanr: {details['genre']}")
        else:
            details['genre'] = "N/A"

        # 5. TRAJANJE
        duration_match = re.search(r'<h4>Trajanje:</h4>\s*(.*?)</br>', content, re.DOTALL)
        if duration_match:
            details['duration'] = duration_match.group(1).strip()
            print(f"DEBUG: Trajanje: {details['duration']}")
        else:
            details['duration'] = "N/A"

        # 6. REŽIJA
        director_match = re.search(r'<h4>Režija:</h4>(.*?)</br>', content, re.DOTALL)
        if director_match:
            director_text = director_match.group(1).strip()
            soup2 = BeautifulSoup(director_text, 'html.parser')
            details['director'] = soup2.get_text(strip=True)
            print(f"DEBUG: Režija: {details['director']}")
        else:
            details['director'] = "N/A"

        # 7. SCENARIO
        writer_match = re.search(r'<h4>Scenario:</h4>(.*?)</br>', content, re.DOTALL)
        if writer_match:
            writer_text = writer_match.group(1).strip()
            soup2 = BeautifulSoup(writer_text, 'html.parser')
            details['writer'] = soup2.get_text(strip=True)
            print(f"DEBUG: Scenario: {details['writer']}")
        else:
            details['writer'] = "N/A"

        # 8. GLAVNE ULOGE
        cast_start = content.find('<h4>Glavne uloge:</h4>')
        if cast_start != -1:
            cast_end = content.find('</br></div>', cast_start)
            if cast_end != -1:
                cast_html = content[cast_start:cast_end]
                soup2 = BeautifulSoup(cast_html, 'html.parser')
                actor_links = soup2.find_all('a', class_='moviePersonPopup')
                actors = []
                for link in actor_links:
                    span = link.find('span', itemprop='name')
                    if span:
                        actors.append(span.get_text(strip=True))
                details['cast'] = ', '.join(actors) if actors else "N/A"
                print(f"DEBUG: Glumci ({len(actors)}): {', '.join(actors[:3])}...")
            else:
                details['cast'] = "N/A"
        else:
            details['cast'] = "N/A"

        # 9. IMDb
        imdb_elem = soup.find('a', class_='imdb')
        details['imdb'] = "IMDb link" if imdb_elem else "N/A"

        # 10. Rotten Tomatoes
        tomato_elem = soup.find('a', class_='tomato')
        if tomato_elem:
            details['rotten_tomatoes'] = tomato_elem.get_text(strip=True)
        else:
            details['rotten_tomatoes'] = "N/A"

        # 11. Ocena korisnika
        rating_elem = soup.find('div', class_='ratingGraph')
        if rating_elem:
            style = rating_elem.get('style', '')
            width_match = re.search(r'width:(\d+)px', style)
            if width_match:
                width = int(width_match.group(1))
                details['user_rating'] = f"{width / 10:.1f}/10"
            else:
                details['user_rating'] = "N/A"
        else:
            details['user_rating'] = "N/A"

        # 12. POSTER URL
        poster_elem = soup.find('img', class_='cover', itemprop='image')
        if poster_elem:
            details['poster_url'] = poster_elem.get('src', '')
            print(f"DEBUG: Poster URL: {details['poster_url']}")
        else:
            details['poster_url'] = ''

        print(f"DEBUG: Parsiranje završeno")
        return details

    except Exception as e:
        print(f"Greška pri parsiranju detalja: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_poster(poster_url, movie_id):
    """Preuzima poster i vraća putanju"""
    if not poster_url or not poster_url.startswith('http'):
        print(f"DEBUG: Nevalidan poster URL: {poster_url}")
        return None

    try:
        ensure_cache()

        # Kreiraj jedinstveno ime fajla
        if movie_id:
            filename = f"poster_{movie_id}.jpg"
        else:
            # Koristi hash URL-a
            import hashlib
            url_hash = hashlib.md5(poster_url.encode()).hexdigest()
            filename = f"poster_{url_hash}.jpg"

        poster_path = os.path.join(CACHE_DIR, filename)

        # Proveri da li je već preuzeto (sa proverom veličine)
        if os.path.exists(poster_path):
            file_size = os.path.getsize(poster_path)
            if file_size > 1024:  # Ako je veći od 1KB
                print(f"DEBUG: Poster već postoji ({file_size} bajtova): {poster_path}")
                return poster_path
            else:
                print(f"DEBUG: Poster postoji ali je mali ({file_size} bajtova), ponovo preuzimam")
                os.remove(poster_path)

        print(f"DEBUG: Preuzimam poster sa: {poster_url}")

        # Preuzmi sliku
        req = urllib.request.Request(
            poster_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://rs.titlovi.com/"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                # Pročitaj podatke
                data = response.read()

                # Proveri da li je validna slika
                if len(data) > 1024:
                    with open(poster_path, 'wb') as f:
                        f.write(data)

                    print(f"DEBUG: Poster sačuvan ({len(data)} bajtova): {poster_path}")
                    return poster_path
                else:
                    print(f"DEBUG: Preuzeti poster je previše mali ({len(data)} bajtova)")
                    return None
            else:
                print(f"DEBUG: Greška HTTP {response.status} pri preuzimanju")
                return None

    except Exception as e:
        print(f"Greška pri preuzimanju postera: {e}")
        import traceback
        traceback.print_exc()
        return None

def search_movies(query):
    """Pretražuje filmove po upitu - POBOLJŠANA VERZIJA"""
    if not query or len(query.strip()) < 2:
        return []

    search_url = f"https://rs.titlovi.com/pretraga/?s={quote_plus(query)}"

    try:
        html = download(search_url)

        print(f"DEBUG search_movies: Pretraga za '{query}'")
        print(f"DEBUG: HTML dužina: {len(html)}")

        results = []
        seen_titles = set()

        # Bolji pattern za pronalaženje filmova u rezultatima pretrage
        # Traži linkove koji sadrže /filmovi/ i imaju smislen naslov
        movie_patterns = [
            r'<a[^>]*href="(/filmovi/[^"]+)"[^>]*>\s*(.+?)\s*</a>',
            r'<a[^>]*href="(https://rs\.titlovi\.com/filmovi/[^"]+)"[^>]*>\s*(.+?)\s*</a>',
            r'<h3[^>]*><a[^>]*href="([^"]+)"[^>]*>(.+?)</a></h3>',
        ]

        for pattern in movie_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for href, title in matches:
                title = re.sub(r'<[^>]+>', '', title).strip()

                if len(title) < 2 or title in seen_titles:
                    continue

                # Proveri da li je to film (sadrži filmovi u URL-u)
                if '/filmovi/' not in href.lower():
                    continue

                seen_titles.add(title)

                # Popuni puni URL
                if href.startswith('/'):
                    url = "https://rs.titlovi.com" + href
                elif href.startswith('http'):
                    url = href
                else:
                    continue

                # Ekstraktuj ID iz URL-a
                movie_id = None
                parts = url.split('/')
                for part in parts:
                    if part.isdigit() and len(part) > 3:
                        movie_id = part
                        break

                results.append({
                    "title": title,
                    "url": url,
                    "id": movie_id
                })

                if len(results) >= 25:
                    break

            if results:
                break

        print(f"DEBUG search_movies: Pronađeno {len(results)} filmova")

        # Ako nema rezultata, pokušaj jednostavniji pattern
        if not results:
            print("DEBUG: Pokušavam alternativni pattern...")
            # Traži sve linkove i filtriraj
            all_links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{3,100})</a>', html)
            for href, title in all_links:
                title = re.sub(r'<[^>]+>', '', title).strip()

                if len(title) < 3 or title in seen_titles:
                    continue

                # Filtriraj samo filmove
                if '/filmovi/' in href.lower() and not any(
                        x in href.lower() for x in ['category', 'tag', 'page', 'search', 'login']):
                    seen_titles.add(title)

                    if href.startswith('/'):
                        url = "https://rs.titlovi.com" + href
                    elif href.startswith('http'):
                        url = href
                    else:
                        continue

                    results.append({
                        "title": title,
                        "url": url,
                        "id": None
                    })

                    if len(results) >= 15:
                        break

        return results

    except Exception as e:
        print(f"Greška u search_movies: {e}")
        import traceback
        traceback.print_exc()
        return []


def universal_search(search_params):
    """
    Vrši naprednu univerzalnu pretragu na titlovi.com

    :param search_params: dict sa parametrima:
        - type: 'film', 'serija', 'sve'
        - name: naziv za pretragu
        - year_from: od godine (npr. "2020")
        - year_to: do godine (npr. "2023")
        - genre: žanr (npr. "drama")
        - sort: 'godini prikazivanja', 'popularnosti', 'imdb oceni'
        - imdb_id: IMDB ID (npr. "tt1234567")
    :return: list rezultata
    """
    try:
        # Odredi osnovni URL na osnovu tipa pretrage
        if search_params.get('type') == 'film':
            base_url = "https://rs.titlovi.com/filmovi/"
        elif search_params.get('type') == 'serija':
            base_url = "https://rs.titlovi.com/serije/"
        else:  # 'sve' ili nedefinisano - koristimo /prevodi/
            base_url = "https://rs.titlovi.com/prevodi/"

        # Parametri za URL
        params = []

        # Dodaj tekst pretrage - koristi 'q' parametar (ne 's')
        if search_params.get('name'):
            params.append(f"q={quote_plus(search_params['name'])}")

        # Dodaj godine - koristi iste parametre kao na sajtu
        if search_params.get('year_from') and search_params.get('year_from') != '-1':
            params.append(f"gFrom={search_params['year_from']}")

        if search_params.get('year_to') and search_params.get('year_to') != '-1':
            params.append(f"gTo={search_params['year_to']}")

        # Dodaj sortiranje
        sort_map = {
            'godini prikazivanja': '4',
            'popularnosti': '1',
            'imdb oceni': '5',
            'korisničkoj oceni': '6',
            'naslovu a-z': '1',
            'naslovu z-a': '2',
            'vremenu dodavanja': '6',
            'vremenu ažuriranja': '7'
        }

        # Default sort je 'godini prikazivanja' (4) kao na sajtu
        sort_value = sort_map.get(search_params.get('sort', 'godini prikazivanja'), '4')
        params.append(f"sort={sort_value}")

        # Kreiraj konačni URL
        if params:
            search_url = f"{base_url}?{'&'.join(params)}"
        else:
            search_url = base_url

        print(f"DEBUG universal_search: URL: {search_url}")

        # Preuzmi HTML
        html = download(search_url)

        # DEBUG: Sačuvaj HTML za analizu
        with open('/tmp/titlovi_search.html', 'w', encoding='utf-8') as f:
            f.write(html[:10000] + "\n...\n")

        # Parsiraj rezultate na osnovu tipa stranice
        results = []

        # Proveri da li se radi o stranici sa filmovima ili serijama
        is_movies_page = '/filmovi/' in base_url
        is_series_page = '/serije/' in base_url
        is_all_page = '/prevodi/' in base_url

        # Glavni regex za pronalaženje rezultata - adaptiran za HTML koji si poslao
        if is_series_page:
            # Za serije - pronađi sve <li> elemente unutar <ul class="serije">
            # Iz HTML-a koji si poslao: <ul class="serije"> <li class=""> ... </li> </ul>

            # Prvo pokušaj da nađeš glavni kontejner
            series_pattern = r'<ul\s+class="serije"[^>]*>(.*?)</ul>'
            series_match = re.search(series_pattern, html, re.DOTALL | re.IGNORECASE)

            if series_match:
                series_html = series_match.group(1)

                # Sada pronađi sve <li> elemente unutar ovog ul
                li_pattern = r'<li[^>]*>(.*?)</li>'
                li_matches = re.findall(li_pattern, series_html, re.DOTALL)

                for li_html in li_matches:
                    try:
                        # Pronađi link
                        link_pattern = r'<a\s+href="(/serije/[^"]+)"[^>]*>'
                        link_match = re.search(link_pattern, li_html)
                        if not link_match:
                            continue

                        href = link_match.group(1)

                        # Pronađi naslov
                        title_pattern = r'<h3><a[^>]+>([^<]+)</a>'
                        title_match = re.search(title_pattern, li_html)
                        if title_match:
                            title = title_match.group(1).strip()
                        else:
                            # Alternativni način: nađi bilo koji tekst u linku
                            alt_title_pattern = r'<a[^>]+>([^<]+)</a>'
                            alt_match = re.search(alt_title_pattern, li_html)
                            if alt_match:
                                title = alt_match.group(1).strip()
                            else:
                                continue

                        # Pronađi godinu
                        year = "N/A"
                        year_pattern = r'<i>\((\d{4})\)</i>'
                        year_match = re.search(year_pattern, li_html)
                        if year_match:
                            year = year_match.group(1)

                        # Pronađi thumbnail
                        thumbnail = None
                        img_pattern = r'<img[^>]+src="([^"]+)"[^>]+class="cover"'
                        img_match = re.search(img_pattern, li_html)
                        if img_match:
                            thumbnail = img_match.group(1)

                        # Ekstraktuj ID iz URL-a
                        item_id = None
                        if '-3220592/' in href:
                            item_id = '3220592'
                        elif '-2937338/' in href:
                            item_id = '2937338'
                        else:
                            # Opšti slučaj: poslednji broj u URL-u
                            id_match = re.search(r'-(\d+)/', href)
                            if id_match:
                                item_id = id_match.group(1)

                        # Dodaj u rezultate
                        results.append({
                            "title": title,
                            "url": "https://rs.titlovi.com" + href,
                            "id": item_id,
                            "type": "series",
                            "year": year,
                            "thumbnail": thumbnail,
                            "genres": ""
                        })

                    except Exception as e:
                        print(f"Greška pri parsiranju li elementa: {e}")
                        continue

            else:
                print("DEBUG: Nije pronađen <ul class='serije'> u HTML-u")
                # Alternativni način: pronađi sve linkove ka serijama
                link_pattern = r'<a\s+href="(/serije/[^/]+-\d+/)"[^>]*>([^<]+)</a>'
                link_matches = re.findall(link_pattern, html, re.IGNORECASE)

                for href, title in link_matches:
                    title = title.strip()
                    if len(title) > 2:
                        # Ekstraktuj ID
                        item_id = None
                        id_match = re.search(r'-(\d+)/', href)
                        if id_match:
                            item_id = id_match.group(1)

                        results.append({
                            "title": title,
                            "url": "https://rs.titlovi.com" + href,
                            "id": item_id,
                            "type": "series",
                            "year": "N/A",
                            "thumbnail": None,
                            "genres": ""
                        })

        elif is_movies_page:
            # Za filmove - slična logika
            # Prvo pokušaj da nađeš glavni kontejner
            movies_pattern = r'<ul\s+class="movies"[^>]*>(.*?)</ul>'
            movies_match = re.search(movies_pattern, html, re.DOTALL | re.IGNORECASE)

            if movies_match:
                movies_html = movies_match.group(1)

                # Sada pronađi sve <li> elemente unutar ovog ul
                li_pattern = r'<li[^>]*>(.*?)</li>'
                li_matches = re.findall(li_pattern, movies_html, re.DOTALL)

                for li_html in li_matches:
                    try:
                        # Pronađi link
                        link_pattern = r'<a\s+href="(/filmovi/[^"]+)"[^>]*>'
                        link_match = re.search(link_pattern, li_html)
                        if not link_match:
                            continue

                        href = link_match.group(1)

                        # Pronađi naslov
                        title_pattern = r'<h3><a[^>]+>([^<]+)</a>'
                        title_match = re.search(title_pattern, li_html)
                        if title_match:
                            title = title_match.group(1).strip()
                        else:
                            # Alternativni način
                            alt_title_pattern = r'<a[^>]+>([^<]+)</a>'
                            alt_match = re.search(alt_title_pattern, li_html)
                            if alt_match:
                                title = alt_match.group(1).strip()
                            else:
                                continue

                        # Pronađi godinu
                        year = "N/A"
                        year_pattern = r'<i>\((\d{4})\)</i>'
                        year_match = re.search(year_pattern, li_html)
                        if year_match:
                            year = year_match.group(1)

                        # Dodaj u rezultate
                        results.append({
                            "title": title,
                            "url": "https://rs.titlovi.com" + href,
                            "id": href.split('-')[-1].replace('/', '') if '-' in href else None,
                            "type": "film",
                            "year": year,
                            "thumbnail": None,
                            "genres": ""
                        })

                    except Exception as e:
                        print(f"Greška pri parsiranju filma: {e}")
                        continue

            else:
                # Alternativni način za filmove
                link_pattern = r'<a\s+href="(/filmovi/[^/]+-\d+/)"[^>]*>([^<]+)</a>'
                link_matches = re.findall(link_pattern, html, re.IGNORECASE)

                for href, title in link_matches:
                    title = title.strip()
                    if len(title) > 2:
                        results.append({
                            "title": title,
                            "url": "https://rs.titlovi.com" + href,
                            "id": href.split('-')[-1].replace('/', '') if '-' in href else None,
                            "type": "film",
                            "year": "N/A",
                            "thumbnail": None,
                            "genres": ""
                        })

        else:  # /prevodi/ stranica
            # Prvo pokušaj da nađeš sve linkove ka filmovima i serijama
            link_pattern = r'<a\s+href="(/(filmovi|serije)/[^/]+-\d+/)"[^>]*>([^<]+)</a>'
            link_matches = re.findall(link_pattern, html, re.IGNORECASE)

            for href, item_type, title in link_matches:
                title = title.strip()
                if len(title) > 2:
                    # Odredi tip
                    result_type = "film" if 'filmovi' in href else "series"

                    # Ekstraktuj ID
                    item_id = None
                    id_match = re.search(r'-(\d+)/', href)
                    if id_match:
                        item_id = id_match.group(1)

                    results.append({
                        "title": title,
                        "url": "https://rs.titlovi.com" + href,
                        "id": item_id,
                        "type": result_type,
                        "year": "N/A",
                        "thumbnail": None,
                        "genres": ""
                    })

        # Filtriraj duplikate
        unique_results = []
        seen_urls = set()

        for item in results:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])

                # Proveri da li je tip u skladu sa zahtevanim filterom
                if search_params.get('type') == 'sve' or search_params.get('type') == item['type']:
                    unique_results.append(item)

        print(f"DEBUG universal_search: Pronađeno {len(unique_results)} rezultata")

        # Ako nema rezultata, možda treba da proverimo da li je HTML drugačiji
        if len(unique_results) == 0:
            print("DEBUG: HTML prvih 2000 karaktera:", html[:2000])
            print("DEBUG: Proveravam da li postoji 'Stranger Things' u HTML-u:", "Stranger Things" in html)

        return unique_results

    except Exception as e:
        print(f"Greška u universal_search: {e}")
        import traceback
        traceback.print_exc()
        return []
