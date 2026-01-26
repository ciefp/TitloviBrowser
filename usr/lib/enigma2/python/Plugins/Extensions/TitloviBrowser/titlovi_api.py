# titlovi_api.py
# Originalni TitloviAPI iz CiefpOpenSubtitles plugina
# Na početku titlovi_api.py dodajte:
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    print("DEBUG: requests library not available, using urllib fallback")
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.parse
    
import os
import re
import time
import requests
from urllib.parse import quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CACHE_DIR = "/tmp/Titlovi_Browser/Subtitles"
CACHE_TTL = 3600  # 1 sat

class TitloviAPI:
    """Klasa za Titlovi.com - NOVI WORKFLOW (podržava naziv i IMDB ID)"""

    def __init__(self):
        self.base_url = "https://rs.titlovi.com"
        self.search_url = "https://rs.titlovi.com/prevodi/"
        self.session = requests.Session()

        # Realni browser headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'sr-RS,sr,en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://rs.titlovi.com/',
            'Cache-Control': 'max-age=0'
        }

        # Retry mehanizam
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Cookie jar
        self.session.cookies.clear()
        
        # Inicijalizuj cache
        self._ensure_cache()

    def _ensure_cache(self):
        """Osiguraj da cache direktorijum postoji"""
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)

    def search(self, query, languages=None, season=None, episode=None):
        """
        Pretraga na Titlovi.com

        Podržava:
        - Naziv filma: 'moonfall'
        - IMDB ID: 'tt5834426'
        - Naziv serije: 'stranger things'
        """
        print(f"[TitloviAPI] Searching for: '{query}' (supports both name and IMDB ID)")

        # Titlovi.com podržava sve balkanske jezike
        supported_langs = ['sr', 'hr', 'bs', 'sl', 'mk', 'bg', 'me']

        # Filtriranje jezika - samo balkanski
        filtered_langs = []
        if languages:
            for lang in languages:
                lang_lower = lang.lower().strip()
                if lang_lower == 'all':
                    filtered_langs = supported_langs
                    break
                elif lang_lower in ['srp', 'scc', 'srb', 'sr']:
                    filtered_langs.append('sr')
                elif lang_lower in ['hrv', 'hr']:
                    filtered_langs.append('hr')
                elif lang_lower in ['bos', 'bs']:
                    filtered_langs.append('bs')
                elif lang_lower in ['slv', 'sl']:
                    filtered_langs.append('sl')
                elif lang_lower in ['mkd', 'mk']:
                    filtered_langs.append('mk')
                elif lang_lower in ['bul', 'bg']:
                    filtered_langs.append('bg')
                elif lang_lower in ['cnr', 'me']:
                    filtered_langs.append('me')

        if not filtered_langs:
            filtered_langs = ['sr']  # podrazumevano srpski

        print(f"[TitloviAPI] Languages: {filtered_langs}")

        # KREIRAJ SEARCH PARAMS
        params = {'prevod': query.strip()}

        # Dodaj jezike ako postoje (Titlovi možda podržava jezik filter)
        # Čuvaćemo languages za kasnije filtriranje
        self.last_languages = filtered_langs

        # Dodaj sezonu/epizodu ako je serija
        if season is not None:
            params['s'] = season
        if episode is not None:
            params['e'] = episode

        print(f"[TitloviAPI] Search params: {params}")

        try:
            # KORAK 1: Dobij listu svih prevoda
            response = self.session.get(
                self.search_url,
                params=params,
                headers=self.headers,
                timeout=15
            )

            print(f"[TitloviAPI] Search URL: {response.url}")
            print(f"[TitloviAPI] Status: {response.status_code}")

            if response.status_code != 200:
                print(f"[TitloviAPI] Search failed with status {response.status_code}")
                return []

            # DEBUG: Sačuvaj HTML
            self.save_debug_html(response.text, f"search_{query}")

            # KORAK 2: Parsiraj listu prevoda
            results = self.parse_prevodi_list(response.text, query, response.url)

            # KORAK 3: Filtriraj po jeziku
            filtered_results = self.filter_by_language(results, filtered_langs)

            print(f"[TitloviAPI] Total results: {len(results)}, Filtered by language: {len(filtered_results)}")
            return filtered_results

        except Exception as e:
            print(f"[TitloviAPI] Search error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def advanced_search(self, query, params=None):
        """
        NAPREDNA pretraga koristeći Titlovi.com advanced search parametre
        params mora sadržati sve parametre kao u URL-u sa t=2
        """
        print(f"[TitloviAPI] Advanced search for: '{query}'")
        print(f"[TitloviAPI] Advanced params: {params}")

        if not params:
            params = {}

        # Uvek dodaj t=2 za advanced search
        params['t'] = '2'

        # Bazni URL za advanced search
        search_url = "https://rs.titlovi.com/prevodi/"

        try:
            # Napravite zahtev sa svim parametrima
            response = self.session.get(
                search_url,
                params=params,
                headers=self.headers,
                timeout=15
            )

            print(f"[TitloviAPI] Advanced search URL: {response.url}")
            print(f"[TitloviAPI] Status: {response.status_code}")

            if response.status_code != 200:
                print(f"[TitloviAPI] Advanced search failed: {response.status_code}")
                return []

            # Sačuvaj za debug
            self.save_debug_html(response.text, f"advanced_{query}")

            # Parsiraj rezultate (možemo koristiti postojeću metodu)
            return self.parse_prevodi_list(response.text, query, response.url)

        except Exception as e:
            print(f"[TitloviAPI] Advanced search error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def save_debug_html(self, html, name):
        """Sačuvaj HTML za debug"""
        try:
            timestamp = int(time.time())
            safe_name = name.replace('/', '_').replace('?', '_')[:50]
            debug_path = os.path.join(CACHE_DIR, f"titlovi_{safe_name}_{timestamp}.html")

            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(html)

            print(f"[TitloviAPI] Saved debug HTML: {debug_path}")
        except:
            pass

    def parse_prevodi_list(self, html, query, search_url):
        """Parsiraj listu prevoda sa /prevodi/?prevod=... stranice"""
        print(f"[TitloviAPI] Parsing prevodi list...")

        try:
            import re
            import urllib.parse
            results = []

            # DEBUG: Ispiši sample HTML
            print(f"[TitloviAPI] HTML length: {len(html)} chars")

            # Pronađi sve linkove ka specifičnim prevodima
            # Pattern: /prevodi/naziv-ID/ ili /prevodi/naziv-ID
            prevod_patterns = [
                r'href=["\'](/prevodi/([^"\']+?-(\d+))/?)["\']',
                r'href=["\'][^"\']*?/prevodi/[^"\']*?-(\d+)/?["\']',
                r'data-href=["\']/prevodi/([^"\']+?-(\d+))/["\']'
            ]

            all_matches = []
            for pattern in prevod_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    print(f"[TitloviAPI] Pattern found {len(matches)} matches")
                    all_matches.extend(matches)
                    break  # Koristi prvi pattern koji nađe nešto

            if not all_matches:
                print(f"[TitloviAPI] No prevod links found, trying alternative parsing...")
                # Fallback: traži bilo koje linkove sa brojevima
                alt_pattern = r'href=["\'][^"\']*?/(\d+)/["\']'
                alt_matches = re.findall(alt_pattern, html)
                if alt_matches:
                    print(f"[TitloviAPI] Found {len(alt_matches)} numeric links")
                    # Pretpostavi da su ovo prevod ID-jevi
                    for match in alt_matches:
                        if match.isdigit() and len(match) >= 4:
                            all_matches.append(('', f"film-{match}", match))

            print(f"[TitloviAPI] Total prevod links found: {len(all_matches)}")

            # Grupiši po ID-u da ukloniš duplikate
            unique_prevods = {}

            for match in all_matches:
                if len(match) >= 3:
                    full_match, full_path, prevod_id = match[:3]
                elif len(match) == 1:
                    # Samo ID
                    prevod_id = match[0]
                    full_path = f"film-{prevod_id}"
                else:
                    continue

                if prevod_id.isdigit() and prevod_id not in unique_prevods:
                    # Ekstraktuj naziv iz path-a
                    name_match = re.match(r'([^-]+)-', full_path)
                    name = name_match.group(1) if name_match else "film"

                    unique_prevods[prevod_id] = {
                        'id': prevod_id,
                        'path': full_path,
                        'name': name,
                        'url': f"https://rs.titlovi.com/prevodi/{full_path}/"
                    }

            print(f"[TitloviAPI] Unique prevods: {len(unique_prevods)}")

            # Ako nema prevoda, možda je direktno jedna prevod stranica
            if not unique_prevods:
                print(f"[TitloviAPI] No prevod links, checking if direct prevod page...")
                # Proveri da li je ovo direktna prevod stranica
                if '/prevodi/' in search_url and re.search(r'/prevodi/[^/?]+-\d+/', search_url):
                    print(f"[TitloviAPI] This is a direct prevod page")
                    # Ekstraktuj ID iz URL-a
                    id_match = re.search(r'/prevodi/[^/]+-(\d+)/', search_url)
                    if id_match:
                        prevod_id = id_match.group(1)
                        # Kreiraj jednostavan rezultat
                        simple_result = self.create_simple_result(prevod_id, query, search_url)
                        if simple_result:
                            return [simple_result]

            # Parsiraj detalje za svaki prevod (maks 10 za brzinu)
            prevod_ids = list(unique_prevods.keys())
            for i, prevod_id in enumerate(prevod_ids[:10]):
                try:
                    prevod_info = unique_prevods[prevod_id]

                    print(f"[TitloviAPI] Processing prevod {i + 1}/{min(len(prevod_ids), 10)}: {prevod_id}")

                    # KORAK 3: Poseti specifičnu prevod stranicu za detalje
                    prevod_details = self.fetch_prevod_details(
                        prevod_info['url'],
                        prevod_id,
                        query,
                        fetch_details=(i < 5)  # Detalje samo za prvih 5 za brzinu
                    )

                    if prevod_details:
                        results.append(prevod_details)
                        print(f"[TitloviAPI] ✓ Added prevod {prevod_id}")
                    else:
                        # Kreiraj jednostavan rezultat ako ne možemo dobiti detalje
                        simple_result = self.create_simple_result(prevod_id, query, prevod_info['url'])
                        if simple_result:
                            results.append(simple_result)
                            print(f"[TitloviAPI] Added simple result for {prevod_id}")

                except Exception as e:
                    print(f"[TitloviAPI] Error processing prevod {prevod_id}: {str(e)[:50]}")
                    continue

            print(f"[TitloviAPI] Parsing completed: {len(results)} results")
            return results

        except Exception as e:
            print(f"[TitloviAPI] Parse prevodi list error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def fetch_prevod_details(self, prevod_url, prevod_id, query, fetch_details=True):
        """Poseti specifičnu prevod stranicu i ekstraktuj detalje"""
        if not fetch_details:
            # Ako ne trebaju detalji, kreiraj jednostavan rezultat
            return self.create_simple_result(prevod_id, query, prevod_url)

        try:
            print(f"[TitloviAPI] Fetching details: {prevod_url}")

            response = self.session.get(prevod_url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                print(f"[TitloviAPI] Prevod page failed: {response.status_code}")
                return self.create_simple_result(prevod_id, query, prevod_url)

            html = response.text

            # Ekstraktuj detalje sa prevod stranice
            import re

            # Naslov filma
            title = "Unknown Title"
            title_patterns = [
                r'<h1[^>]*>([^<]+)</h1>',
                r'<title>([^<]+)</title>',
                r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
                r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>'
            ]

            for pattern in title_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    # Očisti title
                    title = title.replace(' - Titlovi.com', '').replace('Titlovi.com', '').strip()
                    if title:
                        break

            # Godina
            year = ""
            year_patterns = [
                r'Godina.*?[:>]\s*(\d{4})',
                r'Year.*?[:>]\s*(\d{4})',
                r'\((\d{4})\)',
                r'<span[^>]*class="[^"]*year[^"]*"[^>]*>(\d{4})</span>'
            ]

            for pattern in year_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    year = match.group(1)
                    break

            # Jezik
            language = "srpski"
            lang_patterns = [
                r'Jezik.*?[:>]\s*([^<]+)',
                r'Language.*?[:>]\s*([^<]+)',
                r'<td[^>]*>Jezik</td>\s*<td[^>]*>([^<]+)</td>',
                r'<span[^>]*class="[^"]*language[^"]*"[^>]*>([^<]+)</span>'
            ]

            for pattern in lang_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    language = match.group(1).strip()
                    break

            # Download broj
            downloads = 0
            dl_patterns = [
                r'Preuzimanja.*?[:>]\s*(\d+)',
                r'Downloads.*?[:>]\s*(\d+)',
                r'<td[^>]*>Preuzimanja</td>\s*<td[^>]*>(\d+)</td>',
                r'<span[^>]*class="[^"]*downloads[^"]*"[^>]*>(\d+)</span>'
            ]

            for pattern in dl_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    try:
                        downloads = int(match.group(1))
                    except:
                        pass
                    break

            # Kreiraj rezultat
            result = {
                'title': title[:200],
                'year': year,
                'language': language[:50],
                'language_code': self.get_lang_code(language),
                'downloads': downloads,
                'rating': 0,
                'release_info': self.extract_release_info(html),
                'fps': 0,
                'prevod_id': str(prevod_id),
                'film_id': str(prevod_id),  # Za backward compatibility
                'media_id': str(prevod_id),  # Za backward compatibility
                'prevod_url': prevod_url,
                'prevod_path': prevod_url.replace('https://rs.titlovi.com/prevodi/', '').rstrip('/'),
                'season_info': "",
                'is_series': False,
                'season': None,
                'episode': None,
                'site': 'titlovi',
                'search_query': query,
                'search_method': 'prevod_page'
            }

            # Proveri da li je serija
            series_keywords = ['sezona', 'epizoda', 'season', 'episode', 's0', 'e0']
            html_lower = html.lower()
            for keyword in series_keywords:
                if keyword in html_lower:
                    result['is_series'] = True

                    # Pokušaj ekstraktovati sezonu/epizodu
                    s_match = re.search(r'sezona.*?(\d+)', html_lower, re.IGNORECASE)
                    e_match = re.search(r'epizoda.*?(\d+)', html_lower, re.IGNORECASE)

                    if s_match:
                        try:
                            result['season'] = int(s_match.group(1))
                        except:
                            pass
                    if e_match:
                        try:
                            result['episode'] = int(e_match.group(1))
                        except:
                            pass

                    if result['season'] and result['episode']:
                        result['season_info'] = f"S{result['season']:02d}E{result['episode']:02d}"

                    break

            return result

        except Exception as e:
            print(f"[TitloviAPI] Fetch prevod details error: {e}")
            # Vrati jednostavan rezultat kao fallback
            return self.create_simple_result(prevod_id, query, prevod_url)

    def create_simple_result(self, prevod_id, query, prevod_url):
        """Kreiraj jednostavan rezultat"""
        return {
            'title': f"{query} - {prevod_id}",
            'year': "",
            'language': "srpski",
            'language_code': "srp",
            'downloads': 0,
            'rating': 0,
            'release_info': "",
            'fps': 0,
            'prevod_id': str(prevod_id),
            'film_id': str(prevod_id),
            'media_id': str(prevod_id),
            'prevod_url': prevod_url,
            'prevod_path': prevod_url.replace('https://rs.titlovi.com/prevodi/', '').rstrip('/'),
            'season_info': "",
            'is_series': False,
            'season': None,
            'episode': None,
            'site': 'titlovi',
            'search_query': query,
            'search_method': 'simple'
        }

    def extract_release_info(self, html):
        """Ekstraktuj release info iz HTML-a"""
        import re

        patterns = [
            r'Kvalitet.*?[:>]\s*([^<]+)',
            r'Quality.*?[:>]\s*([^<]+)',
            r'Release.*?[:>]\s*([^<]+)',
            r'<td[^>]*>Kvalitet</td>\s*<td[^>]*>([^<]+)</td>',
            r'<span[^>]*class="[^"]*quality[^"]*"[^>]*>([^<]+)</span>'
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]

        return ""

    def filter_by_language(self, results, languages):
        """Filtriraj rezultate po jeziku"""
        if not languages or 'all' in [l.lower() for l in languages]:
            return results

        filtered = []
        for result in results:
            result_lang = result.get('language', '').lower()
            result_lang_code = result.get('language_code', '').lower()

            # Proveri da li se podudara sa traženim jezicima
            match = False
            for lang in languages:
                lang_lower = lang.lower()
                if (lang_lower in result_lang or
                        result_lang_code.startswith(lang_lower) or
                        lang_lower.startswith(result_lang_code)):
                    match = True
                    break

            if match:
                filtered.append(result)

        return filtered

    def get_lang_code(self, language):
        """Konvertuj naziv jezika u kod"""
        lang_map = {
            'srpski': 'srp', 'српски': 'srp', 'serbian': 'srp',
            'hrvatski': 'hrv', 'croatian': 'hrv',
            'bosanski': 'bos', 'bosnian': 'bos',
            'slovenački': 'slv', 'slovenian': 'slv',
            'slovenski': 'slv',
            'makedonski': 'mkd', 'macedonian': 'mkd',
            'bugarski': 'bul', 'bulgarian': 'bul',
            'crnogorski': 'cnr', 'montenegrin': 'cnr',
            'engleski': 'eng', 'english': 'eng'
        }

        lang_lower = language.lower()
        for key, code in lang_map.items():
            if key in lang_lower:
                return code

        return 'srp'  # podrazumevano

    def download(self, media_id, title=""):
        """
        Preuzimanje titla sa Titlovi.com

        Podržava:
        - result dict (sa prevod_url)
        - string prevod_id
        """
        print(f"[TitloviAPI] Download called with: {type(media_id)}")

        # Ako je result dict (sa prevod_url), koristi ga
        if isinstance(media_id, dict):
            result = media_id
            prevod_url = result.get('prevod_url', '')
            prevod_id = result.get('prevod_id') or result.get('film_id') or result.get('media_id')
            download_title = result.get('title', title)

            if not prevod_url and prevod_id:
                # Konstruiši URL ako ga nema
                prevod_path = result.get('prevod_path', f"film-{prevod_id}")
                prevod_url = f"https://rs.titlovi.com/prevodi/{prevod_path}/"

            print(f"[TitloviAPI] Downloading from result, prevod_url: {prevod_url}")
            return self.download_from_prevod_url(prevod_url, prevod_id, download_title)

        # Ako je samo string ID
        if isinstance(media_id, str) and media_id.isdigit():
            print(f"[TitloviAPI] Downloading with prevod_id: {media_id}")
            # Konstruiši URL
            prevod_url = f"https://rs.titlovi.com/prevodi/film-{media_id}/"
            return self.download_from_prevod_url(prevod_url, media_id, title)

        print(f"[TitloviAPI] Invalid media_id type: {type(media_id)}")
        return None

    def download_from_prevod_url(self, prevod_url, prevod_id, title=""):
        """Download sa specifične prevod stranice - GLAVNA METODA"""
        print(f"[TitloviAPI] Download from prevod URL: {prevod_url}")

        try:
            # KORAK 1: Poseti prevod stranicu
            response = self.session.get(prevod_url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                print(f"[TitloviAPI] Prevod page failed: {response.status_code}")
                return None

            html = response.text

            # Sačuvaj za debug
            self.save_debug_html(html, f"prevod_{prevod_id}")

            # KORAK 2: Pronađi download link
            download_url = self.find_download_link(html, prevod_id, prevod_url)

            if not download_url:
                print(f"[TitloviAPI] No download link found, trying direct download...")
                # Pokušaj direktno sa ?download=1
                direct_url = f"{prevod_url}?download=1"
                print(f"[TitloviAPI] Trying direct: {direct_url}")

                response2 = self.session.get(direct_url, headers=self.headers, timeout=15)
                if response2.status_code == 200 and len(response2.content) > 100:
                    return self.process_download_content(response2.content, f"direct_{prevod_id}")

                return None

            print(f"[TitloviAPI] Found download URL: {download_url}")

            # KORAK 3: Preuzmi sa download URL-a
            response3 = self.session.get(download_url, headers=self.headers, timeout=30)

            if response3.status_code == 200 and len(response3.content) > 100:
                result = self.process_download_content(response3.content, f"download_{prevod_id}")

                # Dodaj metadata za identifikaciju
                if isinstance(result, dict):
                    result['prevod_id'] = prevod_id
                    result['title'] = title
                    result['source'] = 'titlovi'

                return result
            else:
                print(f"[TitloviAPI] Download failed: {response3.status_code}, size: {len(response3.content)}")

                # Pokušaj POST metodom
                print(f"[TitloviAPI] Trying POST method...")

                post_url = "https://rs.titlovi.com/download/"
                post_data = {
                    'id': prevod_id,
                    'type': '1'
                }

                # Dodaj referer header
                post_headers = self.headers.copy()
                post_headers['Referer'] = prevod_url
                post_headers['Content-Type'] = 'application/x-www-form-urlencoded'

                response4 = self.session.post(post_url, data=post_data, headers=post_headers, timeout=30)
                if response4.status_code == 200 and len(response4.content) > 100:
                    return self.process_download_content(response4.content, f"post_{prevod_id}")

            return None

        except Exception as e:
            print(f"[TitloviAPI] Download error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def find_download_link(self, html, prevod_id, prevod_url):
        """Pronađi download link na prevod stranici"""
        import re

        # Pattern 1: Form action
        form_patterns = [
            r'<form[^>]*action=["\']([^"\']*download[^"\']*)["\'][^>]*>',
            r'<form[^>]*id="downloadForm"[^>]*action=["\']([^"\']+)["\']'
        ]

        for pattern in form_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                action = match.group(1)
                if not action.startswith('http'):
                    action = 'https://rs.titlovi.com' + action
                print(f"[TitloviAPI] Found form action: {action}")
                return action

        # Pattern 2: Download link/button
        link_patterns = [
            r'href=["\']([^"\']*download[^"\']*id=' + re.escape(prevod_id) + r'[^"\']*)["\']',
            r'href=["\']([^"\']*download\.php\?[^"\']*)["\']',
            r'href=["\']([^"\']*/download/\?[^"\']*)["\']',
            r'<a[^>]*class="[^"]*download[^"]*"[^>]*href=["\']([^"\']+)["\']',
            r'<button[^>]*onclick=["\']window\.location=\'([^\']+)\'["\']'
        ]

        for pattern in link_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match:
                    url = match
                    if not url.startswith('http'):
                        url = 'https://rs.titlovi.com' + url
                    print(f"[TitloviAPI] Found download link: {url}")
                    return url

        # Pattern 3: Meta refresh (redirect)
        meta_pattern = r'<meta[^>]*http-equiv="refresh"[^>]*content="[^"]*url=([^"]+)"'
        meta_match = re.search(meta_pattern, html, re.IGNORECASE)
        if meta_match:
            url = meta_match.group(1)
            if not url.startswith('http'):
                url = 'https://rs.titlovi.com' + url
            print(f"[TitloviAPI] Found meta refresh to: {url}")
            return url

        return None

    def process_download_content(self, content, source_name):
        """Procesiraj download content (ZIP ili direktan SRT)"""
        print(f"[TitloviAPI] Processing download content from {source_name}, size: {len(content)} bytes")

        # Proveri da li je ZIP
        if content[:2] == b'PK':
            print(f"[TitloviAPI] ZIP file detected - extracting ALL SRT files")
            result = self.extract_from_zip(content)

            # Vrati kompletan result dict umesto samo fajla
            return result

        # Proveri da li je direktan SRT/WebVTT
        if self.is_subtitle_content(content):
            print(f"[TitloviAPI] Direct subtitle file detected")
            return content

        # Ako nije ništa od navedenog, možda je HTML sa error-om
        try:
            text = content[:1000].decode('utf-8', errors='ignore')
            if '<html' in text.lower() or '<!doctype' in text.lower():
                print(f"[TitloviAPI] HTML response instead of subtitle")
                # Sačuvaj za debug
                debug_path = os.path.join(CACHE_DIR, f"titlovi_error_{source_name}.html")
                with open(debug_path, 'wb') as f:
                    f.write(content)
                print(f"[TitloviAPI] Saved error HTML to {debug_path}")
        except:
            pass

        return content  # Vrati šta god da je

    def extract_from_zip(self, zip_content):
        """Ekstraktuj SRT iz ZIP fajla - NOVO: vraća SVE SRT fajlove kao listu"""
        try:
            from io import BytesIO
            from zipfile import ZipFile, BadZipFile

            print(f"[TitloviAPI] Extracting ZIP, size: {len(zip_content)} bytes")

            zipfile = ZipFile(BytesIO(zip_content))
            file_list = zipfile.namelist()
            print(f"[TitloviAPI] ZIP contains {len(file_list)} files: {file_list}")

            # Pronađi SVE SRT fajlove
            srt_files = []
            for filename in file_list:
                if filename.lower().endswith('.srt'):
                    print(f"[TitloviAPI] Found SRT: {filename}")
                    content = zipfile.read(filename)
                    srt_files.append({
                        'name': filename,
                        'content': content,
                        'size': len(content)
                    })

            # NOVO: Ako ima SRT fajlova, vrati LISTU
            if srt_files:
                print(f"[TitloviAPI] Found {len(srt_files)} SRT files")

                # Za backward compatibility: vrati i najveći fajl
                # Ali takođe vraćamo listu svih fajlova
                largest_srt = max(srt_files, key=lambda x: x['size'])

                # Log koji su svi SRT fajlovi
                for srt in srt_files:
                    print(f"[TitloviAPI] Available SRT: {srt['name']} ({srt['size']} bytes)")

                print(f"[TitloviAPI] Returning {len(srt_files)} SRT files")

                # Vrati tuple: (najveći_fajl, lista_svih_fajlova)
                return {
                    'largest': largest_srt['content'],
                    'all_srt': srt_files,
                    'is_zip': True,
                    'file_count': len(srt_files)
                }

            # Ako nema SRT fajlova, probaj druge formate
            extensions_order = ['.sub', '.txt', '.ass', '.ssa', '.vtt']

            for ext in extensions_order:
                for filename in file_list:
                    if filename.lower().endswith(ext):
                        print(f"[TitloviAPI] Extracting {filename}")
                        content = zipfile.read(filename)
                        print(f"[TitloviAPI] Extracted {len(content)} bytes from {filename}")

                        if len(content) > 10:
                            return {
                                'largest': content,
                                'all_srt': [{'name': filename, 'content': content, 'size': len(content)}],
                                'is_zip': True,
                                'file_count': 1
                            }

            # Ako nema tekstualnih fajlova, vrati prvi
            if file_list:
                filename = file_list[0]
                print(f"[TitloviAPI] No text files, extracting first: {filename}")
                content = zipfile.read(filename)
                return {
                    'largest': content,
                    'all_srt': [{'name': filename, 'content': content, 'size': len(content)}],
                    'is_zip': True,
                    'file_count': 1
                }

            print(f"[TitloviAPI] ZIP is empty")
            return {
                'largest': zip_content,
                'all_srt': [],
                'is_zip': True,
                'file_count': 0
            }

        except BadZipFile:
            print(f"[TitloviAPI] Not a valid ZIP file")
            return {
                'largest': zip_content,
                'all_srt': [],
                'is_zip': False,
                'file_count': 0
            }
        except Exception as e:
            print(f"[TitloviAPI] ZIP extraction error: {e}")
            return {
                'largest': zip_content,
                'all_srt': [],
                'is_zip': False,
                'file_count': 0
            }

    def is_subtitle_content(self, content):
        """Proveri da li je content subtitle fajl"""
        if not content or len(content) < 10:
            return False

        try:
            text = content[:1000].decode('utf-8', errors='ignore')

            # SRT format
            if re.search(r'\d+\s*\r?\n\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}', text):
                return True

            # WebVTT format
            if text.strip().startswith('WEBVTT'):
                return True

            # SUB/IDX format
            if text.startswith('{') and '}' in text:
                return True

            # ASS/SSA format
            if '[Script Info]' in text:
                return True

        except:
            pass

        return False

# Wrapper funkcije za kompatibilnost sa postojećim plugin-om
def search_subtitles_basic(search_text, year="", language="scc"):
    """Wrapper za osnovnu pretragu"""
    api = TitloviAPI()
    # Konvertuj language code
    lang_map = {
        'scc': 'srp', 'sr': 'srp', 'srp': 'srp',
        'hr': 'hrv', 'hrv': 'hrv',
        'bs': 'bos', 'bos': 'bos',
        'sl': 'slv', 'slv': 'slv',
        'mk': 'mkd', 'mkd': 'mkd',
        'bg': 'bul', 'bul': 'bul',
        'en': 'eng', 'eng': 'eng'
    }
    lang_code = lang_map.get(language.lower(), 'srp')
    
    # Konvertuj rezultate u format koji plugin očekuje
    results = api.search(search_text, [lang_code])
    return convert_api_results(results)
    
def search_subtitles_advanced(search_text, imdb_id="", season="", episode="", year="", language="scc", params=None):
    """
    Napredna pretraga titlova (za serije)
    """
    print(f"DEBUG: Advanced search: {search_text}, imdb: {imdb_id}, S{season}E{episode}, year: {year}")
    
    # Ako su dati params, koristi advanced search
    if params:
        print(f"DEBUG: Using advanced search with params: {params}")
        api = TitloviAPI()
        results = api.advanced_search(search_text or imdb_id, params)
        return convert_api_results(results)
    
    # Inače koristi standardnu logiku
    if not search_text or len(search_text.strip()) < 2:
        return []
    
    # Ako ima season/episode, to je serija
    if season or episode:
        return search_series_subtitles(search_text, season, episode, language)
    
    # Inače koristi standardnu pretragu
    return search_subtitles_basic(search_text, year, language)
    
    # Konvertuj language code
    lang_map = {
        'scc': 'srp', 'sr': 'srp', 'srp': 'srp',
        'hr': 'hrv', 'hrv': 'hrv',
        'bs': 'bos', 'bos': 'bos',
        'sl': 'slv', 'slv': 'slv',
        'mk': 'mkd', 'mkd': 'mkd',
        'bg': 'bul', 'bul': 'bul',
        'en': 'eng', 'eng': 'eng'
    }
    lang_code = lang_map.get(language.lower(), 'srp')
    
    # Ako ima IMDB ID, dodaj ga u query
    if imdb_id:
        search_text = f"{search_text} {imdb_id}"
    
    # Konvertuj sezonu/epizodu
    season_num = int(season) if season and season.isdigit() else None
    episode_num = int(episode) if episode and episode.isdigit() else None
    
    # Pretraži
    results = api.search(search_text, [lang_code], season_num, episode_num)
    return convert_api_results(results)

def convert_api_results(api_results):
    """Konvertuje API rezultate u format koji plugin očekuje"""
    converted = []
    
    for result in api_results:
        converted.append({
            'title': result.get('title', 'Unknown'),
            'url': result.get('prevod_url', ''),
            'id': result.get('prevod_id', ''),
            'language': result.get('language', 'srpski'),
            'language_code': result.get('language_code', 'srp'),
            'format': 'srt',  # Pretpostavka
            'downloads': result.get('downloads', 0),
            'year': result.get('year', ''),
            'release': result.get('release_info', ''),
            'fps': result.get('fps', ''),
            'type': 'series' if result.get('is_series') else 'movie'
        })
    
    return converted


def download_subtitle_file(subtitle_url, filename=None):
    """Download subtitle from result dictionary or prevod URL"""
    import os
    import requests
    import re
    import zipfile
    import io

    # Uvezi get_download_path iz plugina
    try:
        from Plugins.Extensions.TitloviBrowser.plugin import get_download_path
        download_folder = get_download_path()
    except:
        # Fallback ako ne može da se uveze
        download_folder = "/media/hdd/subtitles/"

    print(f"[TitloviAPI] Download folder: {download_folder}")

    # Kreiraj folder ako ne postoji
    try:
        os.makedirs(download_folder, exist_ok=True)
    except:
        pass

    try:
        # Ako je prosleđen dict (rezultat pretrage)
        if isinstance(subtitle_url, dict):
            result = subtitle_url
            prevod_url = result.get('url')
            if not prevod_url:
                print("[TitloviAPI] ✗ No URL in result dict")
                return None

            print(f"[TitloviAPI] Downloading from result, prevod_url: {prevod_url}")
            url = prevod_url
        else:
            # Ako je prosleđen string URL
            url = subtitle_url
            result = {}

        print(f"[TitloviAPI] Download from URL: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Referer': 'https://rs.titlovi.com/'
        }

        # Prvo dobij detalje stranice da nađemo download link
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Sačuvaj debug HTML
        debug_dir = os.path.join("/tmp/Titlovi_Browser", "Subtitles")
        os.makedirs(debug_dir, exist_ok=True)
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        debug_file = os.path.join(debug_dir, f"titlovi_prevod_{url_hash}_{int(time.time())}.html")
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)

        # Pronađi download link
        download_url = None
        download_patterns = [
            r'href=["\'](https://rs\.titlovi\.com/download/\?type=1&mediaid=\d+)["\']',
            r'href=["\'](/download/\?type=1&mediaid=\d+)["\']',
            r'href=["\'](download/\?type=1&mediaid=\d+)["\']',
            r'<a[^>]*href=["\'][^"\']*download[^"\']*mediaid=(\d+)[^"\']*["\']',
        ]

        for pattern in download_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                if pattern.startswith('href=["\'](https://'):
                    download_url = matches[0]
                else:
                    # Relativni URL
                    download_url = f"https://rs.titlovi.com{matches[0] if matches[0].startswith('/') else '/' + matches[0]}"
                break

        if not download_url:
            # Pokušaj alternativni način
            mediaid_match = re.search(r'mediaid=(\d+)', response.text)
            if mediaid_match:
                mediaid = mediaid_match.group(1)
                download_url = f"https://rs.titlovi.com/download/?type=1&mediaid={mediaid}"

        if not download_url:
            print("[TitloviAPI] ✗ Could not find download URL")
            return None

        print(f"[TitloviAPI] Found download URL: {download_url}")

        # Sada download-uj fajl
        response = requests.get(download_url, headers=headers, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        content = response.content

        print(f"[TitloviAPI] Processing download content, size: {len(content)} bytes")

        # Proveri da li je ZIP fajl
        if content_type == 'application/zip' or content[:4] == b'PK\x03\x04':
            print("[TitloviAPI] ZIP file detected - extracting SRT files")

            # Ekstraktuj ZIP
            zip_buffer = io.BytesIO(content)
            available_srts = []

            try:
                with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                    for file_info in zip_file.infolist():
                        if file_info.filename.lower().endswith('.srt'):
                            file_content = zip_file.read(file_info)
                            available_srts.append({
                                'name': file_info.filename,
                                'content': file_content,
                                'size': len(file_content)
                            })
                            print(f"[TitloviAPI] Found SRT: {file_info.filename}")
            except zipfile.BadZipFile:
                print("[TitloviAPI] ✗ Invalid ZIP file")
                return None

            if not available_srts:
                print("[TitloviAPI] ✗ No SRT files in ZIP")
                return None

            print(f"[TitloviAPI] Found {len(available_srts)} SRT files")

            # Odaberi prvi SRT fajl (možeš da promeniš logiku ako treba specifičan jezik)
            srt_info = available_srts[0]
            subtitle_content = srt_info['content']
            original_filename = srt_info['name']

            print(f"[TitloviAPI] Using SRT: {original_filename} ({srt_info['size']} bytes)")
        else:
            # Direktan SRT fajl
            subtitle_content = content

            # Pokušaj da dobiješ originalno ime
            original_filename = None
            if 'content-disposition' in response.headers:
                cd = response.headers['content-disposition']
                match = re.search(r'filename=["\']?(.*?)["\']?$', cd)
                if match:
                    original_filename = match.group(1)

            if not original_filename:
                # Ekstraktuj iz URL-a
                original_filename = os.path.basename(download_url.split('?')[0])
                if not original_filename or len(original_filename) < 5:
                    original_filename = "subtitle.srt"

        # Odredi finalno ime fajla
        if filename:
            final_filename = filename
        elif isinstance(result, dict) and result.get('title'):
            # Koristi naslov iz rezultata pretrage
            title = result.get('title', 'subtitle')

            # Dodaj dodatne informacije ako postoje
            if result.get('language'):
                lang = result.get('language', '').lower()
                if lang not in title.lower():
                    title = f"{title}_{lang}"

            # Čisti naziv
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', title)

            # Obavezno .srt ekstenzija
            if not clean_name.lower().endswith('.srt'):
                clean_name += '.srt'

            final_filename = clean_name
        elif original_filename:
            # Koristi originalno ime iz ZIP-a ili response-a
            final_filename = original_filename
        else:
            # Fallback
            final_filename = f"subtitle_{int(time.time())}.srt"

        # Osiguraj .srt ekstenziju
        if not final_filename.lower().endswith('.srt'):
            final_filename += '.srt'

        # Čisti ime fajla od nevalidnih karaktera
        final_filename = re.sub(r'[<>:"/\\|?*]', '_', final_filename)

        # Kreiraj punu putanju
        filepath = os.path.join(download_folder, final_filename)

        # Proveri da li fajl već postoji i dodaj broj ako treba
        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(original_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1

        print(f"[TitloviAPI] Saving subtitle to: {filepath}")

        # Sačuvaj fajl
        with open(filepath, 'wb') as f:
            f.write(subtitle_content)

        print(f"[TitloviAPI] ✓ Subtitle saved: {os.path.basename(filepath)} ({len(subtitle_content)} bytes)")
        return filepath

    except Exception as e:
        print(f"[TitloviAPI] ✗ Download error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Alias funkcije za kompatibilnost
parse_subtitles_basic = search_subtitles_basic
parse_subtitles_advanced = search_subtitles_advanced
download_subtitle = download_subtitle_file

# Test funkcija
def test_search():
    """Testira pretragu titlova"""
    print("Testing TitloviAPI search...")
    
    # Test 1: Osnovna pretraga
    print("\n1. Basic search for 'avengers':")
    results = search_subtitles_basic("avengers", "2012", "scc")
    if results:
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.get('title')} - {r.get('language')} (ID: {r.get('id')})")
    else:
        print("  No results")
    
    # Test 2: Napredna pretraga za serije
    print("\n2. Advanced search for 'stranger things':")
    results = search_subtitles_advanced("stranger things", "", "1", "1", "", "scc")
    if results:
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.get('title')} - {r.get('language')} (ID: {r.get('id')})")
    else:
        print("  No results")

if __name__ == "__main__":
    test_search()