from Plugins.Plugin import PluginDescriptor
import sys
import os
# Dodaj import za universal_search ako postoji
try:
    from .parser import universal_search
except ImportError:
    def universal_search(*args, **kwargs):
        print("WARNING: universal_search not available")
        return []
# Dodaj trenutni direktorijum u Python path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

try:
    print(f"DEBUG: Pokušavam da učitam titlovi_api modul")
    from titlovi_api import (
        search_subtitles_basic,
        search_subtitles_advanced,
        download_subtitle_file,
        parse_subtitles_basic,      # Alias
        parse_subtitles_advanced,   # Alias
        download_subtitle           # Alias
    )
    print("DEBUG: TitloviAPI modul uspešno uvezen")
except ImportError as e:
    print(f"DEBUG: Greška pri uvozu titlovi_api modula: {e}")

    def search_subtitles_basic(*args, **kwargs):
        print("WARNING: TitloviAPI module not loaded - search_subtitles_basic")
        return []
    
    def search_subtitles_advanced(*args, **kwargs):
        print("WARNING: TitloviAPI module not loaded - search_subtitles_advanced")
        return []
    
    def download_subtitle_file(*args, **kwargs):
        print("WARNING: TitloviAPI module not loaded - download_subtitle_file")
        return None
    
    # Alias-i
    parse_subtitles_basic = search_subtitles_basic
    parse_subtitles_advanced = search_subtitles_advanced
    download_subtitle = download_subtitle_file
    
from .parser import parse_all_series, parse_series_details, search_series
from .parser import (
    parse_all_series,
    parse_series_details,
    search_series,
    search_movies,
    parse_popular_movies,
    parse_movie_details,
    download_poster,
    CACHE_DIR,
    parse_popular_series,
    parse_new_movies,
    parse_all_movies,
    parse_boxoffice_srbija,
    parse_boxoffice_hrvatska,
    parse_boxoffice_sad,
    universal_search  # DODAJ OVO!
)
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import eListboxPythonMultiContent, gFont, loadPic, ePicLoad
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigText, ConfigPassword, ConfigYesNo, ConfigSelection
from Components.Sources.StaticText import StaticText
from enigma import gRGB
from Tools.Directories import pathExists, fileExists

import os
import threading
from time import sleep
import shutil 

PLUGIN_NAME = "Titlovi Browser"
PLUGIN_VERSION = "1.0"
PLUGIN_PATH = os.path.dirname(__file__)
PLUGIN_DIR = os.path.dirname(__file__) if '__file__' in globals() else "/usr/lib/enigma2/python/Plugins/Extensions/TitloviBrowser"
BACKGROUND = os.path.join(PLUGIN_DIR, "background.png")

# Na početku plugin.py, NAKON import-a, a PRE klasa:

def get_cache_size():
    """Vraća veličinu cache-a"""
    cache_dir = "/tmp/Titlovi_Browser"

    if not os.path.exists(cache_dir):
        return "Cache folder: 0 MB"

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(cache_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)

    size_mb = total_size / (1024 * 1024)
    return f"Trenutna veličina cache-a: {size_mb:.2f} MB"

# Takodje kao globalnu funkciju, posle get_cache_size():

def clear_cache():
    """Briše sav cache iz /tmp/Titlovi_Browser"""
    import shutil
    cache_dir = "/tmp/Titlovi_Browser"

    if os.path.exists(cache_dir):
        try:
            # Obriši ceo folder
            shutil.rmtree(cache_dir)

            # Ponovo kreiraj prazan
            os.makedirs(cache_dir, exist_ok=True)

            return True, f"Cache uspešno obrisan!\n\n{get_cache_size()}"

        except Exception as e:
            return False, f"Greška pri brisanju cache-a:\n{str(e)}"
    else:
        return True, "Cache folder ne postoji."

def get_download_path():
    """Vraća konfigurisanu download putanju"""
    try:
        # Pokušaj da učitaš iz config-a
        import Components.config as config
        download_path = config.plugins.titlovibrowser.downloadpath.value

        # Ako config ne postoji, koristi podrazumevanu
        if not download_path:
            download_path = "/media/hdd/subtitles/"
    except:
        download_path = "/media/hdd/subtitles/"

    # Obavezno dodaj slash na kraju
    if download_path and not download_path.endswith('/'):
        download_path += '/'

    # Kreiraj folder ako ne postoji
    if download_path:
        try:
            os.makedirs(download_path, exist_ok=True)
        except:
            pass

    return download_path

class MovieDetailScreen(Screen):
    skin = """
    <screen name="MovieDetailScreen" position="center,center" size="1920,1080" title="Detalji filma">
        <!-- GLAVNA POZADINA -->
        <eLabel position="0,0" size="1920,1080" backgroundColor="#0f0f0f" zPosition="-2" />

        <!-- LEVI PANEL -->
        <eLabel position="40,30" size="1120,920" backgroundColor="#1e1e1e" zPosition="-1" />

        <!-- DESNI PANEL -->
        <eLabel position="1200,30" size="680,920" backgroundColor="#151515" zPosition="-1" />

        <!-- NASLOV --> 
        <widget name="title" position="60,50" size="1080,70" font="Regular;38" foregroundColor="#FFD700" transparent="1" halign="left" valign="center" /> <!-- 80→70, 42→38 -->

        <!-- PODNASLOV (godina) -->
        <widget name="subtitle" position="60,130" size="1080,30" font="Regular;26" foregroundColor="#f7bf07" transparent="1" /> <!-- 40→30, 28→26 -->

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,170" size="1080,2" backgroundColor="#333" zPosition="1" /> <!-- 180→170 -->

        <!-- ŽANR -->
        <widget name="genre" position="60,190" size="1080,30" font="Regular;28" foregroundColor="#05dffc" transparent="1" /> <!-- 200→190, 40→30, 30→28 -->

        <!-- TRAJANJE -->
        <widget name="duration" position="60,230" size="1080,30" font="Regular;28" foregroundColor="#05dffc" transparent="1" /> <!-- 250→230, 40→30, 30→28 -->

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,270" size="1080,1" backgroundColor="#444" zPosition="1" /> <!-- 300→270 -->

        <!-- OCENE -->
        <widget name="ratings" position="60,280" size="1080,60" font="Regular;26" foregroundColor="white" transparent="1" /> <!-- 320→280, 80→60, 28→26 -->

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,350" size="1080,1" backgroundColor="#444" zPosition="1" /> <!-- 410→350 -->

        <!-- REŽIJA -->
        <widget name="director" position="60,360" size="1080,30" font="Regular;26" foregroundColor="#FF69B4" transparent="1" /> <!-- 430→360, 40→30, 28→26 -->

        <!-- SCENARIO -->
        <widget name="writer" position="60,400" size="1080,30" font="Regular;26" foregroundColor="#9370DB" transparent="1" /> <!-- 480→400, 40→30, 28→26 -->

        <!-- GLUMCI -->
        <widget name="cast" position="60,440" size="1080,60" font="Regular;24" foregroundColor="#FFA500" transparent="1" valign="top" /> <!-- 530→440, 70→60, 26→24 -->

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,510" size="1080,2" backgroundColor="#32CD32" zPosition="1" /> <!-- 610→510 -->

        <!-- OPIS NASLOV -->
        <widget name="plot_label" position="60,520" size="1080,35" font="Regular;30" foregroundColor="#32CD32" transparent="1" /> <!-- 620→520, 40→35, 32→30 -->

        <!-- OPIS TEKST -->
        <widget name="plot" position="60,560" size="1080,350" font="Regular;26" foregroundColor="white" transparent="1" valign="top" /> <!-- 670→560, 270→350, 28→26 -->

        <!-- POSTER -->
        <widget name="poster" position="1220,50" size="660,880" alphatest="blend" zPosition="1" />

        <!-- FOOTER -->
        <eLabel position="0,980" size="1920,100" backgroundColor="#000000" zPosition="0" transparency="150" />

        <ePixmap pixmap="skin_default/buttons/red.png" position="50,1000" size="35,35" alphatest="blend" />
        <eLabel position="100,995" size="200,50" font="Regular;26" foregroundColor="white" backgroundColor="#800000" halign="center" valign="center" text="EXIT - nazad" />

        <ePixmap pixmap="skin_default/buttons/green.png" position="300,1000" size="35,35" alphatest="blend" />
        <eLabel position="350,995" size="200,50" font="Regular;26" foregroundColor="white" backgroundColor="#008000" halign="center" valign="center" text="OK - zatvori" />
    </screen>
    """

    def __init__(self, session, movie, poster_path=None):
        Screen.__init__(self, session)
        self.movie = movie
        self.poster_path = poster_path

        # Inicijalizuj sve widget-e
        self["title"] = Label("")
        self["subtitle"] = Label("")
        self["genre"] = Label("")
        self["duration"] = Label("")
        self["ratings"] = Label("")
        self["director"] = Label("")
        self["writer"] = Label("")
        self["cast"] = Label("")
        self["plot_label"] = Label("OPIS FILMA")
        self["plot"] = Label("")
        self["poster"] = Pixmap()

        # Postavi podatke
        self.updateData()

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "cancel": self.close,
                "ok": self.close,
            },
            -1
        )

        self.onFirstExecBegin.append(self.loadPoster)

    def updateData(self):
        """Ažuriraj sve widget-e sa podacima iz filma"""
        # 1. NASLOV
        title = self.movie.get("title", "")
        self["title"].setText(title)

        # 2. PODNASLOV (godina)
        year = self.movie.get("year", "N/A")
        if year != "N/A":
            self["subtitle"].setText(f"📅 {year}")
        else:
            self["subtitle"].setText("")

        # 3. ŽANR
        genre = self.movie.get("genre", "N/A")
        if genre != "N/A":
            self["genre"].setText(f"🎭 {genre}")
        else:
            self["genre"].setText("")

        # 4. TRAJANJE
        duration = self.movie.get("duration", "N/A")
        if duration != "N/A":
            self["duration"].setText(f"⏱️ {duration}")
        else:
            self["duration"].setText("")

        # 5. OCENE
        ratings_text = self.buildRatingsText()
        self["ratings"].setText(ratings_text)

        # 6. REŽIJA
        director = self.movie.get("director", "N/A")
        if director != "N/A":
            self["director"].setText(f"Režija: {director}")
        else:
            self["director"].setText("")

        # 7. SCENARIO
        writer = self.movie.get("writer", "N/A")
        if writer != "N/A" and writer != director:
            self["writer"].setText(f"Scenario: {writer}")
        else:
            self["writer"].setText("")

        # 8. GLUMCI
        cast = self.movie.get("cast", "N/A")
        if cast != "N/A":
            actors = [a.strip() for a in cast.split(',')] if ',' in cast else [cast.strip()]

            # Ograniči na 4-5 glumaca
            if len(actors) > 5:
                display_actors = actors[:5]
                remaining = len(actors) - 5
                cast_text = ", ".join(display_actors) + f"... (+{remaining})"
            else:
                cast_text = ", ".join(actors)

            # Podeli u dva reda ako je predugačko
            if len(cast_text) > 50:
                parts = cast_text.split(', ')
                if len(parts) >= 2:
                    mid = len(parts) // 2
                    line1 = ', '.join(parts[:mid]) + ','
                    line2 = ', '.join(parts[mid:])
                    cast_text = f"{line1}\n{line2}"

            self["cast"].setText(f"Glumci: {cast_text}")
        else:
            self["cast"].setText("")

        # 9. OPIS
        plot = self.movie.get("plot", "Opis nije dostupan.")
        formatted_plot = self.formatPlot(plot, max_width=60)
        self["plot"].setText(formatted_plot)

    def buildRatingsText(self):
        """Gradi tekst za ocene"""
        ratings = []

        # IMDb - ŽUTA
        imdb = self.movie.get("imdb", "N/A")
        if imdb != "N/A" and imdb != "IMDb link":
            ratings.append(f"⭐ IMDb: {imdb}")

        # Rotten Tomatoes - CRVENA
        rt = self.movie.get("rotten_tomatoes", "N/A")
        if rt != "N/A":
            ratings.append(f"Rotten Tomatoes: {rt}")

        # Korisnička ocena - ZELENA
        user = self.movie.get("user_rating", "N/A")
        if user != "N/A":
            ratings.append(f"Ocena korisnika: {user}")

        if ratings:
            return "   |   ".join(ratings)
        return "Nema ocena"

    def formatPlot(self, text, max_width=60):
        """Formatira opis tako da stane u dostupni prostor"""
        if not text:
            return ""

        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

            # Ograniči na 8 redova
            if len(lines) >= 8:
                if current_line:
                    lines.append(' '.join(current_line))
                break

        if current_line and len(lines) < 8:
            lines.append(' '.join(current_line))

        # Ako je tekst predugačak, dodaj "..."
        if len(lines) == 8 and len(text) > len(' '.join(lines)):
            if lines[-1].endswith('.'):
                lines[-1] = lines[-1][:-1] + "..."
            else:
                lines[-1] = lines[-1] + "..."

        return '\n'.join(lines)

    def loadPoster(self):
        """Učitava poster ako postoji"""
        print(f"DEBUG: Poster path: {self.poster_path}")

        if self.poster_path and os.path.exists(self.poster_path):
            try:
                # Proveri veličinu fajla
                file_size = os.path.getsize(self.poster_path)
                print(f"DEBUG: Poster file size: {file_size} bytes")

                if file_size < 1024:
                    print(f"DEBUG: Poster file too small ({file_size} bytes)")
                    return

                # Pokušaj sa loadPic
                from enigma import loadPic

                # Veličina widget-a je 660x880, ali ostavimo marginu
                pixmap = loadPic(self.poster_path,
                                 640,  # width
                                 860,  # height
                                 True,  # keep aspect
                                 1,  # bilinear
                                 True)  # ignore alpha

                if pixmap:
                    self["poster"].instance.setPixmap(pixmap)
                    self["poster"].instance.show()
                    print("DEBUG: Poster loaded successfully via loadPic")
                else:
                    print("DEBUG: loadPic returned None")

                    # Pokušaj sa ePicLoad
                    try:
                        from enigma import ePicLoad
                        self.picload = ePicLoad()
                        self.picload.PictureData.get().append(self.decodePoster)
                        self.picload.setPara([
                            640,  # width
                            860,  # height
                            1,  # aspect
                            1,  # resize
                            0,  # cache
                            "",  # background
                            "#00000000"
                        ])
                        result = self.picload.startDecode(self.poster_path)
                        print(f"DEBUG: ePicLoad startDecode result: {result}")
                    except Exception as e2:
                        print(f"DEBUG: ePicLoad error: {e2}")

            except Exception as e:
                print(f"DEBUG: Error loading poster: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("DEBUG: No poster to load")

    def decodePoster(self, info):
        """Callback za učitani poster"""
        print(f"DEBUG: decodePoster pozvan, info: {info}")

        try:
            ptr = self.picload.getData()
            if ptr:
                self["poster"].instance.setPixmap(ptr)
                self["poster"].instance.show()
                print("DEBUG: Poster uspešno učitan i prikazan")
            else:
                print("DEBUG: Nema podataka za poster")

                # Pokušaj alternativni način
                try:
                    from enigma import loadPic
                    ptr = loadPic(self.poster_path,
                                  self["poster"].instance.size().width(),
                                  self["poster"].instance.size().height())
                    if ptr:
                        self["poster"].instance.setPixmap(ptr)
                        print("DEBUG: Poster učitan preko loadPic")
                except Exception as e:
                    print(f"DEBUG: Greška pri alternativnom učitavanju: {e}")
        except Exception as e:
            print(f"DEBUG: Error in decodePoster: {e}")

    def showOptions(self):
        """Prikazuje dodatne opcije"""
        menu = [
            ("Preuzmi titlove", self.downloadSubtitles),
            ("Dodaj u omiljene", self.addToFavorites),
            ("Podeli", self.shareMovie),
        ]
        self.session.openWithCallback(
            self.optionSelected,
            ChoiceBox,
            title="Dodatne opcije",
            list=menu
        )

    def optionSelected(self, choice):
        if choice:
            choice[1]()

    def downloadSubtitles(self):
        self.session.open(
            MessageBox,
            "Preuzimanje titlova (u razvoju)",
            MessageBox.TYPE_INFO
        )

    def addToFavorites(self):
        self.session.open(
            MessageBox,
            "Dodato u omiljene!",
            MessageBox.TYPE_INFO
        )

    def shareMovie(self):
        self.session.open(
            MessageBox,
            "Deljenje (u razvoju)",
            MessageBox.TYPE_INFO
        )


class MovieListScreen(Screen):
    skin = """
    <screen name="MovieListScreen" position="center,center" size="1920,1080" title="Lista">
        <!-- BACKGROUND IMAGE -->
        <widget name="background" position="1270,50" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />

        <!-- LEVI PANEL -->
        <eLabel position="20,30" size="1150,850" backgroundColor="#333333" zPosition="-1" />

        <!-- DESNI PANEL -->
        <eLabel position="1220,30" size="600,850" backgroundColor="#333333" zPosition="-1" />

        <!-- LIST WIDGET -->
        <widget name="list" position="50,50" size="1100,800"
            scrollbarMode="showOnDemand" font="Regular;30" itemHeight="45" />

        <!-- FOOTER SA BOJENIM TEKSTOM I SIVOM POZADINOM -->
        <eLabel position="20,920" size="1800,100" backgroundColor="#333333" zPosition="-1" />

        <eLabel position="50,940" size="300,50" font="Regular;26" foregroundColor="red" halign="center" valign="center" text="EXIT - nazad" />
        <eLabel position="500,940" size="300,50" font="Regular;26" foregroundColor="green" halign="center" valign="center" text="OK - detalji" />

        <!-- STATUS BAR -->
        <eLabel position="20,990" size="1800,80" backgroundColor="#333333" zPosition="-1" />
        <widget name="status" position="50,1020" size="1700,40" font="Regular;26" halign="left" valign="center" />
    </screen>
    """ % BACKGROUND

    def __init__(self, session, title, movies):
        Screen.__init__(self, session)
        self.movies = movies
        
        self["background"] = Pixmap()

        self["list"] = MenuList([])
        self["status"] = Label("")

        # SIMPLE ACTIONMAP
        self["actions"] = ActionMap(
            ["DirectionActions", "OkCancelActions"],
            {
                "cancel": self.close,  # EXIT dugme
                "back": self.close,  # BACK dugme
                "ok": self.showDetails,  # OK dugme
                "red": self.close,  # CRVENO dugme
            },
            -1
        )

        self.setTitle(title)
        self.onLayoutFinish.append(self.loadList)

    def loadList(self):
        self.list = []
        for movie in self.movies:
            title = movie.get("title", "Nepoznat naslov")
            if len(title) > 45:
                title = title[:42] + "..."
            self.list.append(title)

        self["list"].setList(self.list)
        self["status"].setText(f"Pronađeno {len(self.movies)} stavki")

    def getCurrentMovie(self):
        idx = self["list"].getSelectedIndex()
        if idx < len(self.movies):
            return self.movies[idx]
        return None

    def showDetails(self):
        movie = self.getCurrentMovie()
        if not movie:
            return

        # Kratka poruka bez callback-a
        self["status"].setText(f"Učitavam: {movie['title']}")

        # Koristi timer za delay
        from enigma import eTimer
        self.details_timer = eTimer()
        self.details_timer.callback.append(lambda: self._openDetails(movie))
        self.details_timer.start(300, True)

    def _openDetails(self, movie):
        """Otvara detalje nakon kratkog delay-a"""
        try:
            details = parse_movie_details(movie["url"])
            poster_path = None

            if details and details.get("poster_url"):
                poster_path = download_poster(details["poster_url"], movie.get("id", ""))

            if not details:
                details = {
                    "title": movie["title"],
                    "plot": "Nije moguće preuzeti detalje",
                    "year": movie.get("year", "N/A"),
                    "genre": movie.get("genre", "N/A"),
                }

            self.session.open(MovieDetailScreen, details, poster_path)

        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

class SearchScreen(Screen):
    skin = """
    <screen name="SearchScreen" position="center,center" size="1920,1080" title="Pretraga">
        <widget name="title" position="50,30" size="1820,60" font="Regular;42" />  <!-- 40 → 42 -->
        <widget name="info" position="50,120" size="1820,100" font="Regular;30" />  <!-- 28 → 30 -->
        <widget name="config" position="50,240" size="1820,200" font="Regular;30" /> <!-- dodaj font -->

        <!-- FOOTER SA BOJENIM TEKSTOM -->
        <eLabel position="50,500" size="400,60" font="Regular;26" foregroundColor="red" text="EXIT - nazad" />
        <eLabel position="500,500" size="500,60" font="Regular;26" foregroundColor="green" text="ZELENO - pretraži" />
        <eLabel position="1100,500" size="500,60" font="Regular;26" foregroundColor="yellow" text="OK - tastatura" />
        <widget name="status" position="50,580" size="1820,60" font="Regular;26" />
    </screen>
    """

    # U klasi SearchScreen dodaj ovu metodu:
    def searchSeries(self, query):
        """Pretražuje serije"""
        try:
            results = search_series(query)

            if not results:
                self.session.open(
                    MessageBox,
                    f"Nema rezultata za: {query}",
                    type=MessageBox.TYPE_INFO,
                    timeout=3
                )
                self["status"].setText("Nema rezultata")
                return

            # Otvori listu rezultata serija
            self.session.open(SeriesSearchScreen, f"Serije: {query}", results)

        except Exception as e:
            error_msg = f"Greška pri pretrazi serija:\n{str(e)}"
            self.session.open(
                MessageBox,
                error_msg,
                type=MessageBox.TYPE_ERROR,
                timeout=5
            )

    # U SearchScreen klasi, ažuriraj _doSearchNow:
    def _doSearchNow(self, query):
        """Vrši pretragu"""
        try:
            # Pita korisnika da li želi da traži filmove ili serije
            menu = [
                ("Pretraži filmove", "search_movies"),
                ("Pretraži serije", "search_series"),
            ]

            self.session.openWithCallback(
                lambda choice: self._performSearch(choice, query),
                ChoiceBox,
                title=f"Pretraga: {query}",
                list=menu
            )

        except Exception as e:
            error_msg = f"Greška pri pretrazi:\n{str(e)}"
            self.session.open(
                MessageBox,
                error_msg,
                type=MessageBox.TYPE_ERROR,
                timeout=5
            )

    def _performSearch(self, choice, query):
        if not choice:
            return

        search_type = choice[1]

        if search_type == "search_movies":
            results = search_movies(query)
            if results:
                self.session.open(SimpleMoviesSearchScreen, f"Filmovi: {query}", results)
            else:
                self.session.open(MessageBox, f"Nema filmova za: {query}", MessageBox.TYPE_INFO)
        elif search_type == "search_series":
            results = search_series(query)
            if results:
                self.session.open(SeriesSearchScreen, f"Serije: {query}", results)
            else:
                self.session.open(MessageBox, f"Nema serija za: {query}", MessageBox.TYPE_INFO)

# Dodaj ovu klasu u plugin.py
class SimpleSeriesScreen(Screen):
    """VEOMA JEDNOSTAVAN SCREEN za prikaz serija"""

    skin = """
    <screen name="SimpleSeriesScreen" position="center,center" size="1920,1080" title="Serije">
    
        <!-- LEVI PANEL -->
        <eLabel position="20,30" size="1150,850" backgroundColor="#333333" zPosition="-1" />

        <!-- DESNI PANEL -->
        <eLabel position="1220,30" size="600,850" backgroundColor="#333333" zPosition="-1" />

        <!-- BACKGROUND -->
        <widget name="background" position="1250,50" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />
        
        <!-- LIST WIDGET -->
        <widget name="list" position="50,50" size="1100,800"
            scrollbarMode="showOnDemand" font="Regular;30" itemHeight="45" />

        <!-- FOOTER SA BOJENIM TEKSTOM I SIVOM POZADINOM -->
        <eLabel position="20,920" size="1800,100" backgroundColor="#333333" zPosition="-1" />
        <widget name="status" position="50,970" size="1700,40" font="Regular;26" />
    </screen>
    """ % BACKGROUND

    def __init__(self, session):
        Screen.__init__(self, session)

        self["background"] = Pixmap()
        self["list"] = MenuList([])
        self["status"] = Label("Učitavam...")

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "cancel": self.close,
                "ok": self.showDetails,
            },
            -1
        )

        self.setTitle("Serije")
        self.onLayoutFinish.append(self.loadSeries)

        self.series = []

    def loadSeries(self):
        """Učitava serije"""
        try:
            # Pretpostavljam da postoji funkcija parse_all_series analognia parse_all_movies
            # Ako ne postoji, moraš je implementirati ili koristiti drugačiju funkciju
            data = parse_all_series(max_results=60)  # ← ovo bi trebalo vraćati dict
            self.series = data.get("items", [])  # ← OBAVEZNO uzmi "items"!

            print("[DEBUG] Broj serija iz parsera:", len(self.series))  # ← dodaj ovo

            list_entries = []
            for series in self.series:
                title = series.get("title", "Nepoznat naslov")
                if len(title) > 45:
                    title = title[:42] + "..."
                list_entries.append(title)

            self["list"].setList(list_entries)

            if self.series:
                self["status"].setText(f"Pronađeno {len(self.series)} serija")
            else:
                self["status"].setText("Nema serija")

        except Exception as e:
            print("[SimpleSeriesScreen] Greška:", str(e))
            self["status"].setText("Greška pri učitavanju serija")

    def _loadSeriesNow(self):
        """Stvarno učitava serije"""
        try:
            data = parse_all_series(1, 4)
            self.series = data.get("items", [])

            # Kreiraj listu stringova za MenuList
            display_list = []
            for series in self.series:
                title = series.get("title", "Nepoznato")
                year = series.get("year", "")
                if year != "N/A":
                    title = f"{title} ({year})"

                if len(title) > 45:
                    title = title[:42] + "..."
                display_list.append(title)

            self["list"].setList(display_list)
            self["status"].setText(f"Pronađeno {len(self.series)} serija")

        except Exception as e:
            self["status"].setText(f"Greška pri učitavanju: {str(e)}")
            # Dodaj neke test podatke za slučaj greške
            self.series = [
                {"title": "Test Serija 1", "url": "https://rs.titlovi.com/", "year": "2024"},
                {"title": "Test Serija 2", "url": "https://rs.titlovi.com/", "year": "2023"}
            ]
            self["list"].setList(["Test Serija 1 (2024)", "Test Serija 2 (2023)"])

    def getCurrentSeries(self):
        """Vraća trenutno selektovanu seriju"""
        try:
            idx = self["list"].getSelectedIndex()
            if idx < len(self.series):
                return self.series[idx]
        except:
            pass
        return None

    def showDetails(self):
        """Prikazuje detalje serije"""
        series = self.getCurrentSeries()
        if not series:
            self["status"].setText("Nije selektovana serija")
            return

        self["status"].setText(f"Učitavam: {series.get('title', 'N/A')}")

        from enigma import eTimer
        self.details_timer = eTimer()
        self.details_timer.callback.append(lambda: self._openDetails(series))
        self.details_timer.start(500, True)

    # U klasi SimpleSeriesScreen, zameni _openDetails metod:
    def _openDetails(self, series):
        """Otvara detalje serije"""
        try:
            details = parse_series_details(series["url"])
            poster_path = None

            if details and details.get("poster_url"):
                poster_path = download_poster(details["poster_url"], series.get("id", ""))

            if not details:
                details = {
                    "title": series.get("title", "Nepoznata serija"),
                    "plot": "Nije moguće preuzeti detalje",
                    "year": series.get("year", "N/A"),
                    "genre": series.get("genres", "N/A"),
                    "type": "series"
                }

            # Koristimo NOVI SeriesDetailScreen
            self.session.open(SeriesDetailScreen, details, poster_path)

        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )
            
class SeriesDetailScreen(Screen):
    """Ekran za detalje serije"""

    skin = """
    <screen name="SeriesDetailScreen" position="center,center" size="1920,1080" title="Detalji serije">
        <!-- GLAVNA POZADINA -->
        <eLabel position="0,0" size="1920,1080" backgroundColor="#0f0f0f" zPosition="-2" />

        <!-- LEVI PANEL -->
        <eLabel position="40,30" size="1120,920" backgroundColor="#1e1e1e" zPosition="-1" />

        <!-- DESNI PANEL -->
        <eLabel position="1200,30" size="680,920" backgroundColor="#151515" zPosition="-1" />

        <!-- NASLOV --> 
        <widget name="title" position="60,50" size="1080,70" font="Regular;38" foregroundColor="#FFD700" transparent="1" halign="left" valign="center" />

        <!-- PODNASLOV (godina) -->
        <widget name="subtitle" position="60,130" size="1080,30" font="Regular;26" foregroundColor="#f7bf07" transparent="1" />

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,170" size="1080,2" backgroundColor="#333" zPosition="1" />

        <!-- ŽANR -->
        <widget name="genre" position="60,190" size="1080,30" font="Regular;28" foregroundColor="#05dffc" transparent="1" />

        <!-- TRAJANJE/SEZONE -->
        <widget name="duration" position="60,230" size="1080,30" font="Regular;28" foregroundColor="#05dffc" transparent="1" />

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,270" size="1080,1" backgroundColor="#444" zPosition="1" />

        <!-- OCENE -->
        <widget name="ratings" position="60,280" size="1080,60" font="Regular;26" foregroundColor="white" transparent="1" />

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,350" size="1080,1" backgroundColor="#444" zPosition="1" />

        <!-- REŽIJA -->
        <widget name="director" position="60,360" size="1080,30" font="Regular;26" foregroundColor="#FF69B4" transparent="1" />

        <!-- SCENARIO -->
        <widget name="writer" position="60,400" size="1080,30" font="Regular;26" foregroundColor="#9370DB" transparent="1" />

        <!-- GLUMCI -->
        <widget name="cast" position="60,440" size="1080,60" font="Regular;24" foregroundColor="#FFA500" transparent="1" valign="top" />

        <!-- HORIZONTALNA LINIJA -->
        <eLabel position="60,510" size="1080,2" backgroundColor="#32CD32" zPosition="1" />

        <!-- OPIS NASLOV -->
        <widget name="plot_label" position="60,520" size="1080,35" font="Regular;30" foregroundColor="#32CD32" transparent="1" />

        <!-- OPIS TEKST -->
        <widget name="plot" position="60,560" size="1080,350" font="Regular;26" foregroundColor="white" transparent="1" valign="top" />

        <!-- POSTER -->
        <widget name="poster" position="1220,50" size="660,880" alphatest="blend" zPosition="1" />

        <!-- FOOTER -->
        <eLabel position="0,980" size="1920,100" backgroundColor="#000000" zPosition="0" transparency="150" />

        <ePixmap pixmap="skin_default/buttons/red.png" position="50,1000" size="35,35" alphatest="blend" />
        <eLabel position="100,995" size="200,50" font="Regular;26" foregroundColor="white" backgroundColor="#800000" halign="center" valign="center" text="EXIT - nazad" />

        <ePixmap pixmap="skin_default/buttons/green.png" position="300,1000" size="35,35" alphatest="blend" />
        <eLabel position="350,995" size="200,50" font="Regular;26" foregroundColor="white" backgroundColor="#008000" halign="center" valign="center" text="OK - zatvori" />
    </screen>
    """

    def __init__(self, session, series, poster_path=None):
        Screen.__init__(self, session)
        self.series = series
        self.poster_path = poster_path

        # INICIJALIZUJ SVE WIDGET-E KOJE KORISTIŠ
        self["title"] = Label("")
        self["subtitle"] = Label("")
        self["genre"] = Label("")
        self["duration"] = Label("")
        self["ratings"] = Label("")
        self["director"] = Label("")
        self["writer"] = Label("")
        self["cast"] = Label("")
        self["plot_label"] = Label("OPIS SERIJE")  # OVO JE BITNO
        self["plot"] = Label("")
        self["poster"] = Pixmap()

        # Postavi podatke
        self.updateData()

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "cancel": self.close,
                "ok": self.close,
            },
            -1
        )

        self.onFirstExecBegin.append(self.loadPoster)

    def updateData(self):
        """Ažuriraj sve widget-e sa podacima iz serije"""
        # 1. NASLOV
        title = self.series.get("title", "")
        self["title"].setText(title)

        # 2. PODNASLOV (godina)
        year = self.series.get("year", "N/A")
        if year != "N/A":
            self["subtitle"].setText(f"📅 {year}")
        else:
            self["subtitle"].setText("")

        # 3. ŽANR
        genre = self.series.get("genre", "N/A")
        if genre != "N/A":
            self["genre"].setText(f"🎭 {genre}")
        else:
            self["genre"].setText("")

        # 4. TRAJANJE/SEZONE/EPIZODE
        duration_info = []

        duration = self.series.get("duration", "N/A")
        if duration != "N/A":
            duration_info.append(f"⏱️ {duration}")

        seasons = self.series.get("seasons", "N/A")
        if seasons != "N/A":
            duration_info.append(f"📺 {seasons}")

        episodes = self.series.get("episodes", "N/A")
        if episodes != "N/A":
            duration_info.append(f"🎬 {episodes}")

        channel = self.series.get("channel", "N/A")
        if channel != "N/A":
            duration_info.append(f"📡 {channel}")

        if duration_info:
            self["duration"].setText(" | ".join(duration_info))
        else:
            self["duration"].setText("")

        # 5. OCENE
        ratings_text = self.buildRatingsText()
        self["ratings"].setText(ratings_text)

        # 6. REŽIJA
        director = self.series.get("director", "N/A")
        if director != "N/A":
            self["director"].setText(f"Režija: {director}")
        else:
            self["director"].setText("")

        # 7. SCENARIO
        writer = self.series.get("writer", "N/A")
        if writer != "N/A" and writer != director:
            self["writer"].setText(f"Scenario: {writer}")
        else:
            self["writer"].setText("")

        # 8. GLUMCI
        cast = self.series.get("cast", "N/A")
        if cast != "N/A":
            actors = [a.strip() for a in cast.split(',')] if ',' in cast else [cast.strip()]

            # Ograniči na 4-5 glumaca
            if len(actors) > 5:
                display_actors = actors[:5]
                remaining = len(actors) - 5
                cast_text = ", ".join(display_actors) + f"... (+{remaining})"
            else:
                cast_text = ", ".join(actors)

            # Podeli u dva reda ako je predugačko
            if len(cast_text) > 50:
                parts = cast_text.split(', ')
                if len(parts) >= 2:
                    mid = len(parts) // 2
                    line1 = ', '.join(parts[:mid]) + ','
                    line2 = ', '.join(parts[mid:])
                    cast_text = f"{line1}\n{line2}"

            self["cast"].setText(f"Glumci: {cast_text}")
        else:
            self["cast"].setText("")

        # 9. OPIS
        plot = self.series.get("plot", "Opis nije dostupan.")
        formatted_plot = self.formatPlot(plot, max_width=60)
        self["plot"].setText(formatted_plot)

    def buildRatingsText(self):
        """Gradi tekst za ocene"""
        ratings = []

        # IMDb - ŽUTA
        imdb = self.series.get("imdb", "N/A")
        if imdb != "N/A" and imdb != "IMDb link":
            ratings.append(f"⭐ IMDb: {imdb}")

        # Rotten Tomatoes - CRVENA
        rt = self.series.get("rotten_tomatoes", "N/A")
        if rt != "N/A":
            ratings.append(f"Rotten Tomatoes: {rt}")

        # Korisnička ocena - ZELENA
        user = self.series.get("user_rating", "N/A")
        if user != "N/A":
            ratings.append(f"Ocena korisnika: {user}")

        if ratings:
            return "   |   ".join(ratings)
        return "Nema ocena"

    def formatPlot(self, text, max_width=60):
        """Formatira opis tako da stane u dostupni prostor"""
        if not text:
            return ""

        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

            # Ograniči na 8 redova
            if len(lines) >= 8:
                if current_line:
                    lines.append(' '.join(current_line))
                break

        if current_line and len(lines) < 8:
            lines.append(' '.join(current_line))

        # Ako je tekst predugačak, dodaj "..."
        if len(lines) == 8 and len(text) > len(' '.join(lines)):
            if lines[-1].endswith('.'):
                lines[-1] = lines[-1][:-1] + "..."
            else:
                lines[-1] = lines[-1] + "..."

        return '\n'.join(lines)

    def loadPoster(self):
        """Učitava poster ako postoji"""
        print(f"DEBUG: Poster path za seriju: {self.poster_path}")

        if self.poster_path and os.path.exists(self.poster_path):
            try:
                # Proveri veličinu fajla
                file_size = os.path.getsize(self.poster_path)
                print(f"DEBUG: Poster file size: {file_size} bytes")

                if file_size < 1024:
                    print(f"DEBUG: Poster file too small ({file_size} bytes)")
                    return

                # Pokušaj sa loadPic
                from enigma import loadPic

                pixmap = loadPic(self.poster_path,
                                 640,  # width
                                 860,  # height
                                 True,  # keep aspect
                                 1,  # bilinear
                                 True)  # ignore alpha

                if pixmap:
                    self["poster"].instance.setPixmap(pixmap)
                    self["poster"].instance.show()
                    print("DEBUG: Poster loaded successfully via loadPic")
                else:
                    print("DEBUG: loadPic returned None")

                    # Pokušaj sa ePicLoad
                    try:
                        from enigma import ePicLoad
                        self.picload = ePicLoad()
                        self.picload.PictureData.get().append(self.decodePoster)
                        self.picload.setPara([
                            640,  # width
                            860,  # height
                            1,  # aspect
                            1,  # resize
                            0,  # cache
                            "",  # background
                            "#00000000"
                        ])
                        result = self.picload.startDecode(self.poster_path)
                        print(f"DEBUG: ePicLoad startDecode result: {result}")
                    except Exception as e2:
                        print(f"DEBUG: ePicLoad error: {e2}")

            except Exception as e:
                print(f"DEBUG: Error loading poster: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("DEBUG: No poster to load")

    def decodePoster(self, info):
        """Callback za učitani poster"""
        print(f"DEBUG: decodePoster pozvan, info: {info}")

        try:
            ptr = self.picload.getData()
            if ptr:
                self["poster"].instance.setPixmap(ptr)
                self["poster"].instance.show()
                print("DEBUG: Poster uspešno učitan i prikazan")
            else:
                print("DEBUG: Nema podataka za poster")

                # Pokušaj alternativni način
                try:
                    from enigma import loadPic
                    ptr = loadPic(self.poster_path,
                                  self["poster"].instance.size().width(),
                                  self["poster"].instance.size().height())
                    if ptr:
                        self["poster"].instance.setPixmap(ptr)
                        print("DEBUG: Poster učitan preko loadPic")
                except Exception as e:
                    print(f"DEBUG: Greška pri alternativnom učitavanju: {e}")
        except Exception as e:
            print(f"DEBUG: Error in decodePoster: {e}")

class SeriesSearchScreen(SimpleSeriesScreen):
    """Nasleđuje SimpleSeriesScreen za prikaz rezultata pretrage serija"""

    def __init__(self, session, title, series):
        # Pozovi parent konstruktor
        Screen.__init__(self, session)

        self["list"] = MenuList([])
        self["status"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "cancel": self.close,
                "ok": self.showDetails,
            },
            -1
        )

        self.setTitle(title)
        self.series = series

        # Učitaj odmah
        self.onLayoutFinish.append(self.loadSearchResults)

    def loadSearchResults(self):
        """Učitava rezultate pretrage serija"""
        display_list = []
        for series in self.series:
            title = series.get("title", "Nepoznato")
            year = series.get("year", "")
            if year != "N/A":
                title = f"{title} ({year})"

            if len(title) > 45:
                title = title[:42] + "..."
            display_list.append(title)

        self["list"].setList(display_list)
        self["status"].setText(f"{len(self.series)} rezultata")

    # Ovi metodi će naslediti iz SimpleSeriesScreen
    # Ili ih možeš kopirati:
    def getCurrentSeries(self):
        """Vraća trenutno selektovanu seriju"""
        try:
            idx = self["list"].getSelectedIndex()
            if idx < len(self.series):
                return self.series[idx]
        except:
            pass
        return None

    def showDetails(self):
        """Prikazuje detalje serije"""
        series = self.getCurrentSeries()
        if not series:
            self["status"].setText("Nije selektovana serija")
            return

        self["status"].setText(f"Učitavam: {series.get('title', 'N/A')}")

        from enigma import eTimer
        self.details_timer = eTimer()
        self.details_timer.callback.append(lambda: self._openDetails(series))
        self.details_timer.start(500, True)

    def _openDetails(self, series):
        """Otvara detalje serije"""
        try:
            details = parse_series_details(series["url"])
            poster_path = None

            if details and details.get("poster_url"):
                poster_path = download_poster(details["poster_url"], series.get("id", ""))

            if not details:
                details = {
                    "title": series.get("title", "Nepoznata serija"),
                    "plot": "Nije moguće preuzeti detalje",
                    "year": series.get("year", "N/A"),
                    "genre": series.get("genres", "N/A"),
                    "type": "series"
                }

            # Koristimo NOVI SeriesDetailScreen
            self.session.open(SeriesDetailScreen, details, poster_path)

        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )


class SimpleMoviesScreen(Screen):
    skin = """
    <screen name="SimpleMoviesScreen" position="center,center" size="1920,1080" title="Filmovi">
        <!-- BACKGROUND IMAGE -->
        <widget name="background" position="1270,50" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />

        <!-- LEVI PANEL -->
        <eLabel position="20,30" size="1150,850" backgroundColor="#333333" zPosition="-1" />

        <!-- DESNI PANEL -->
        <eLabel position="1220,30" size="600,850" backgroundColor="#333333" zPosition="-1" />

        <!-- LIST WIDGET -->
        <widget name="list" position="50,50" size="1100,800" 
                scrollbarMode="showOnDemand" font="Regular;30" itemHeight="45" />

        <!-- FOOTER SA BOJENIM TEKSTOM I SIVOM POZADINOM -->
        <eLabel position="20,920" size="1800,150" backgroundColor="#333333" zPosition="-1" />

        <eLabel position="50,940" size="300,40" font="Regular;26" foregroundColor="red" halign="center" valign="center" text="EXIT - nazad" />
        <eLabel position="500,940" size="300,40" font="Regular;26" foregroundColor="green" halign="center" valign="center" text="OK - odaberi" />
        <eLabel position="950,940" size="300,40" font="Regular;26" foregroundColor="yellow" halign="center" valign="center" text="ŽUTO - pretraga" />

        <!-- STATUS BAR -->
        <eLabel position="20,990" size="1800,60" backgroundColor="#333333" zPosition="-1" />
        <widget name="status" position="50,1020" size="1700,40" font="Regular;26" halign="left" valign="center" />
    </screen>
    """ % BACKGROUND

    def __init__(self, session):
        Screen.__init__(self, session)

        # PRAVILNO inicijalizuj MenuList sa PRAZNOM listom
        self["background"] = Pixmap()
        self["list"] = MenuList([])
        self["status"] = Label("Učitavam...")

        # VEOMA JEDNOSTAVAN ActionMap
        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "cancel": self.close,
                "ok": self.showDetails,
            },
            -1
        )

        self.setTitle("Filmovi")
        self.onLayoutFinish.append(self.loadMovies)

        # Inicijalizuj praznu listu za filmove
        self.movies = []

    def loadMovies(self):
        try:
            data = parse_all_movies(max_results=60)  # ← ovo vraća dict
            self.movies = data.get("items", [])  # ← OBAVEZNO uzmi "items"!

            print("[DEBUG] Broj filmova iz parsera:", len(self.movies))  # ← dodaj ovo

            list_entries = []
            for movie in self.movies:
                title = movie.get("title", "Nepoznat naslov")
                if len(title) > 45:
                    title = title[:42] + "..."
                list_entries.append(title)

            self["list"].setList(list_entries)

            if self.movies:
                self["status"].setText(f"Pronađeno {len(self.movies)} filmova")
            else:
                self["status"].setText("Nema filmova")

        except Exception as e:
            print("[SimpleMoviesScreen] Greška:", str(e))
            self["status"].setText("Greška pri učitavanju")

    def _loadMoviesNow(self):
        """Stvarno učitava filmove"""
        try:
            data = parse_all_movies(1, 4)
            self.movies = data.get("items", [])

            # Kreiraj listu stringova za MenuList
            display_list = []
            for movie in self.movies:
                title = movie.get("title", "Nepoznato")
                if len(title) > 45:
                    title = title[:42] + "..."
                display_list.append(title)

            # OVO JE KLJUČNO: setList OČEKIJE LISTU STRINGOVA
            self["list"].setList(display_list)
            self["status"].setText(f"Pronađeno {len(self.movies)} filmova")

        except Exception as e:
            self["status"].setText(f"Greška pri učitavanju: {str(e)}")
            # Dodaj neke test podatke za slučaj greške
            self.movies = [
                {"title": "Test Film 1", "url": "https://rs.titlovi.com/"},
                {"title": "Test Film 2", "url": "https://rs.titlovi.com/"}
            ]
            self["list"].setList(["Test Film 1", "Test Film 2"])

    def getCurrentMovie(self):
        """Vraća trenutno selektovani film"""
        try:
            idx = self["list"].getSelectedIndex()
            if idx < len(self.movies):
                return self.movies[idx]
        except:
            pass
        return None

    def showDetails(self):
        """Prikazuje detalje filma"""
        movie = self.getCurrentMovie()
        if not movie:
            self["status"].setText("Nije selektovan film")
            return

        self["status"].setText(f"Učitavam: {movie.get('title', 'N/A')}")

        # Koristi timer za delay
        from enigma import eTimer
        self.details_timer = eTimer()
        self.details_timer.callback.append(lambda: self._openDetails(movie))
        self.details_timer.start(500, True)

    def _openDetails(self, movie):
        """Otvara detalje"""
        try:
            details = parse_movie_details(movie["url"])
            poster_path = None

            if details and details.get("poster_url"):
                poster_path = download_poster(details["poster_url"], movie.get("id", ""))

            if not details:
                details = {
                    "title": movie.get("title", "Nepoznat film"),
                    "plot": "Nije moguće preuzeti detalje",
                    "year": movie.get("year", "N/A"),
                    "genre": movie.get("genres", "N/A"),
                }

            self.session.open(MovieDetailScreen, details, poster_path)

        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )


class SimpleMoviesSearchScreen(SimpleMoviesScreen):
    """Nasleđuje SimpleMoviesScreen za prikaz rezultata pretrage"""

    def __init__(self, session, title, movies):
        Screen.__init__(self, session)

        self["list"] = MenuList([])
        self["status"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "cancel": self.close,
                "ok": self.showDetails,
            },
            -1
        )

        self.setTitle(title)
        self.movies = movies

        # Učitaj odmah (bez timera)
        self.onLayoutFinish.append(self.loadSearchResults)

    def loadSearchResults(self):
        """Učitava rezultate pretrage"""
        display_list = []
        for movie in self.movies:
            title = movie.get("title", "Nepoznato")
            if len(title) > 45:
                title = title[:42] + "..."
            display_list.append(title)

        self["list"].setList(display_list)
        self["status"].setText(f"{len(self.movies)} rezultata")


# Nakon postojećih klasa, dodaj ove nove:

class SubtitlesBasicScreen(Screen):
    skin = """
    <screen name="OpenSubtitlesBasic" position="center,center" size="1920,1080" title="Titlovi Basic">
        <widget name="title" position="50,50" size="1250,60" font="Regular;38" halign="center" valign="center" foregroundColor="#FFD700" />
        
        <!-- SEARCH TEXT -->
        <eLabel position="50,150" size="200,50" font="Regular;30" text="Search text:" />
        <widget name="searchtext" position="300,145" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- YEAR -->
        <eLabel position="50,250" size="200,50" font="Regular;30" text="Year:" />
        <widget name="year" position="300,245" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- LANGUAGE -->
        <eLabel position="50,350" size="200,50" font="Regular;30" text="Language:" />
        <widget name="language" position="300,345" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- BACKGROUND -->
        <widget name="background" position="1400,60" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />
        
        <!-- PANEL -->
        <eLabel position="20,30" size="1920,1000" backgroundColor="#212020" zPosition="-1" />
        
        <!-- STATUS -->
        <widget name="status" position="50,450" size="1250,100" font="Regular;28" />
        
        <!-- FOOTER -->
        <eLabel position="0,980" size="1920,100" backgroundColor="#000000" zPosition="0" />
        
        <eLabel position="50,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="red" text="EXIT" />
        <eLabel position="400,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="green" text="GREEN - Search" />
        <eLabel position="800,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="yellow" text="YELLOW - Keyboard" />
        <eLabel position="1200,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="blue" text="BLUE - Download" />
    </screen>
    """ % BACKGROUND
    
    def __init__(self, session, movie_title=None, movie_year=None):
        Screen.__init__(self, session)
        
        # Lista widget-a za navigaciju
        self.widgets = ["searchtext", "year", "language"]
        self.current_widget_index = 0
        self.last_search_results = []  # Sačuvaj poslednje rezultate
        
        # Inicijalizuj widget-e
        self["title"] = Label("Titlovi Basic Search")
        self["searchtext"] = Label(movie_title or "")
        self["year"] = Label(movie_year or "")
        self["language"] = Label("scc")  # Podrazumevano srpski
        self["status"] = Label("Enter search text and press GREEN to search")
        self["background"] = Pixmap()
        
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.doSearch,
                "yellow": self.openKeyboard,
                "blue": self.downloadCurrent,
                "up": self.moveUp,
                "down": self.moveDown,
                "left": self.moveLeft,
                "right": self.moveRight,
            },
            -1
        )
    
    def moveUp(self):
        """Pomeri se na gornji widget"""
        if self.current_widget_index > 0:
            self.current_widget_index -= 1
    
    def moveDown(self):
        """Pomeri se na donji widget"""
        if self.current_widget_index < len(self.widgets) - 1:
            self.current_widget_index += 1
    
    def moveLeft(self):
        """Pomeri se levo"""
        pass  # Nije potrebno za ovaj screen
    
    def moveRight(self):
        """Pomeri se desno"""
        pass  # Nije potrebno za ovaj screen
    
    def getCurrentWidget(self):
        """Vraća naziv trenutnog widget-a"""
        if self.current_widget_index < len(self.widgets):
            return self.widgets[self.current_widget_index]
        return self.widgets[0]
    
    def openKeyboard(self):
        """Otvara virtuelnu tastaturu za trenutni widget"""
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()
        
        title = f"Enter {current_widget}"
        
        self.session.openWithCallback(
            lambda text: self.keyboardCallback(text, current_widget),
            VirtualKeyBoard,
            title=title,
            text=current_text
        )
    
    def keyboardCallback(self, text, widget_name):
        """Callback nakon unosa sa tastature"""
        if text is not None:
            self[widget_name].setText(text)
            
            # Auto-fokus na sledeći widget (kao u CiefpOpenSubtitles)
            if widget_name == "searchtext":
                self.current_widget_index = 1  # Pređi na Year
            elif widget_name == "year":
                self.current_widget_index = 2  # Pređi na Language
            elif widget_name == "language":
                self.current_widget_index = 0  # Vrati se na Search text
    
    def resetFields(self):
        """Resetuje sva polja"""
        self["searchtext"].setText("")
        self["year"].setText("")
        self["language"].setText("scc")
        self.current_widget_index = 0
        self["status"].setText("Fields reset")
    
    def doSearch(self):
        """Vrši pretragu"""
        search_text = self["searchtext"].getText().strip()
        year = self["year"].getText().strip()
        language = self["language"].getText().strip()
        
        if not search_text or len(search_text) < 2:
            self["status"].setText("Enter at least 2 characters for search")
            return
        
        self["status"].setText(f"Searching for: {search_text}...")
        
        # Vrši pretragu u pozadini
        from enigma import eTimer
        self.search_timer = eTimer()
        self.search_timer.callback.append(
            lambda: self._performSearch(search_text, year, language)
        )
        self.search_timer.start(300, True)

    # U SubtitlesBasicScreen._performSearch():
    def _performSearch(self, search_text, year, language):
        """Vrši stvarnu pretragu"""
        try:
            results = parse_subtitles_basic(search_text, year, language)

            # SAČUVAJ REZULTATE ZA DOWNLOAD
            self.last_search_results = results  # DODAJ OVO

            if not results:
                self["status"].setText(f"No results found for: {search_text}")
                self.session.open(
                    MessageBox,
                    f"No subtitles found for: {search_text}",
                    MessageBox.TYPE_INFO,
                    timeout=3
                )
                return

            # FIXED: Use SubtitlesResultsScreen instead of OpenSubtitlesResults
            self.session.open(SubtitlesResultsScreen, f"Subtitles: {search_text}", results)

        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Search error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    # U OBEMA klasama dodaj ovu metodu:
    def downloadCurrent(self):
        """Download trenutno selektovanog titla sa widget-a"""
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()

        # Za različite widget-e, radi različite stvari
        if current_widget == "searchtext":
            # Ako je searchtext, pretraži ponovo i download prvi rezultat
            self["status"].setText(f"Searching and downloading: {current_text}")
            self.searchAndDownload(current_text)

        elif current_widget == "language":
            # Jezik - samo informacija
            self["status"].setText(f"Selected language: {current_text}")

        elif current_widget == "year":
            # Godina - samo informacija
            self["status"].setText(f"Year: {current_text}")

        elif current_widget == "type":
            # Tip (film/serija) - samo informacija
            self["status"].setText(f"Type: {current_text}")

        elif current_widget in ["season", "episode", "imdbid"]:
            # Ostali parametri - pokaži download meni
            self.showDownloadMenu()

        else:
            # Default: pokaži download meni
            self.showDownloadMenu()

    def searchAndDownload(self, search_text):
        """Pretraži i download prvi rezultat"""
        # Koristi postojeće parametre sa forme
        if isinstance(self, SubtitlesBasicScreen):
            year = self["year"].getText()
            language = self["language"].getText()

            from enigma import eTimer
            self.search_timer = eTimer()
            self.search_timer.callback.append(
                lambda: self._searchAndDownloadBasic(search_text, year, language)
            )
            self.search_timer.start(300, True)

        elif isinstance(self, SubtitlesAdvancedScreen):
            imdb_id = self["imdbid"].getText()
            media_type = self["type"].getText()
            season = self["season"].getText()
            episode = self["episode"].getText()
            year = self["year"].getText()
            language = self["language"].getText()

            from enigma import eTimer
            self.search_timer = eTimer()
            self.search_timer.callback.append(
                lambda: self._searchAndDownloadAdvanced(search_text, imdb_id, media_type,
                                                        season, episode, year, language)
            )
            self.search_timer.start(300, True)

    def _searchAndDownloadBasic(self, search_text, year, language):
        """Pretraži i download za Basic screen"""
        try:
            results = parse_subtitles_basic(search_text, year, language)

            if not results:
                self["status"].setText(f"No results found for: {search_text}")
                self.session.open(
                    MessageBox,
                    f"No subtitles found for: {search_text}",
                    MessageBox.TYPE_INFO,
                    timeout=3
                )
                return

            # Download prvi rezultat
            self.downloadSubtitle(results[0])

        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Search/download error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showDownloadMenu(self):
        """Prikaži meni za download opcije"""
        menu = []

        # Opcija 1: Download poslednje pronađene titlove
        if self.last_search_results:
            menu.append(("Download last search results", "download_last"))

        # Opcija 2: Download izabrani widget
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()
        if current_text and current_text not in ["scc", "tv", "movie"]:
            menu.append((f"Download using '{current_text}'", "download_current"))

        # Opcija 3: Pokreni novu pretragu
        menu.append(("Search and download", "search_download"))

        if menu:
            self.session.openWithCallback(
                self.downloadMenuCallback,
                ChoiceBox,
                title="Download Options",
                list=menu
            )
        else:
            self["status"].setText("No download options available")

    def downloadMenuCallback(self, choice):
        """Callback za download meni"""
        if not choice:
            return

        action = choice[1]

        if action == "download_last" and self.last_search_results:
            # Download prvi titl iz poslednjih rezultata
            self.downloadSubtitle(self.last_search_results[0])

        elif action == "download_current":
            # Download koristeći trenutni widget
            self.downloadCurrent()

        elif action == "search_download":
            # Pokreni ponovno pretragu
            if isinstance(self, SubtitlesBasicScreen):
                self.doSearch()
            elif isinstance(self, SubtitlesAdvancedScreen):
                self.doSearch()

    def downloadSubtitle(self, subtitle):
        """Download specifičan titl"""
        if not subtitle or not subtitle.get('url'):
            self["status"].setText("Invalid subtitle")
            return

        title = subtitle.get('title', 'Unknown')
        self["status"].setText(f"Downloading: {title}")

        # Koristi timer za background download
        from enigma import eTimer
        self.download_timer = eTimer()
        self.download_timer.callback.append(lambda: self._performDownload(subtitle))
        self.download_timer.start(300, True)

    def _performDownload(self, subtitle):
        """Vrši stvarni download"""
        try:
            url = subtitle.get('url')
            if not url:
                self["status"].setText("No download URL")
                return

            # Preuzmi titl
            filepath = download_subtitle(url)

            if filepath:
                filename = os.path.basename(filepath)
                self["status"].setText(f"Downloaded: {filename}")

                self.session.open(
                    MessageBox,
                    f"Subtitle successfully downloaded!\n\n"
                    f"File: {filename}\n"
                    f"Path: {filepath}\n\n"
                    f"The subtitle is now in your download folder.",
                    MessageBox.TYPE_INFO,
                    timeout=5
                )
            else:
                self["status"].setText("Download failed")
                self.session.open(
                    MessageBox,
                    "Failed to download subtitle. Please try again.",
                    MessageBox.TYPE_ERROR
                )

        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Download error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

class SubtitlesAdvancedScreen(SubtitlesBasicScreen):
    skin = """
    <screen name="OpenSubtitlesAdvanced" position="center,center" size="1920,1080" title="Titlovi Advanced">
        <widget name="title" position="50,50" size="1250,60" halign="center" valign="center" font="Regular;38" foregroundColor="#FFD700" />
        
        <!-- SEARCH TEXT -->
        <eLabel position="50,150" size="200,50" font="Regular;30" text="Search text:" />
        <widget name="searchtext" position="300,145" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- IMDB ID -->
        <eLabel position="50,250" size="200,50" font="Regular;30" text="IMDB ID:" />
        <widget name="imdbid" position="300,245" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- TYPE (Film/Series) - DODAJ OVO -->
        <eLabel position="50,350" size="200,50" font="Regular;30" text="Type:" />
        <widget name="type" position="300,345" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- SEASON -->
        <eLabel position="50,450" size="200,50" font="Regular;30" text="Season:" />
        <widget name="season" position="300,445" size="300,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- EPISODE -->
        <eLabel position="700,450" size="200,50" font="Regular;30" text="Episode:" />
        <widget name="episode" position="1000,445" size="300,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- YEAR -->
        <eLabel position="50,550" size="200,50" font="Regular;30" text="Year:" />
        <widget name="year" position="300,545" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- LANGUAGE -->
        <eLabel position="50,650" size="200,50" font="Regular;30" text="Language:" />
        <widget name="language" position="300,645" size="1000,60" font="Regular;30" backgroundColor="#555555" />
        
        <!-- BACKGROUND -->
        <widget name="background" position="1400,60" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />
        
        <!-- STATUS -->
        <widget name="status" position="50,750" size="1250,100" font="Regular;28" />
        
        <!-- PANEL -->
        <eLabel position="20,30" size="1920,1000" backgroundColor="#212020" zPosition="-1" />
        
        <!-- FOOTER -->
        <eLabel position="0,980" size="1920,100" backgroundColor="#000000" zPosition="0" />
        
        <eLabel position="50,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="red" text="EXIT" />
        <eLabel position="400,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="green" text="GREEN - Search" />
        <eLabel position="800,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="yellow" text="YELLOW - Keyboard" />
        <eLabel position="1200,1000" size="300,50" font="Regular;26" halign="center" valign="center" foregroundColor="blue" text="BLUE - Download" />
    </screen>
    """ % BACKGROUND
    
    def __init__(self, session, series_title=None, imdb_id=None, season=None, episode=None, year=None):
        Screen.__init__(self, session)
        
        # Lista widget-a za navigaciju - DODAJ "type"
        self.widgets = ["searchtext", "imdbid", "type", "season", "episode", "year", "language"]
        self.current_widget_index = 0
        self.last_search_results = []  # Sačuvaj poslednje rezultate
        # Inicijalizuj widget-e
        self["title"] = Label("Titlovi Advanced Search")
        self["searchtext"] = Label(series_title or "")
        self["imdbid"] = Label(imdb_id or "")
        self["type"] = Label("tv")  # Default: tv (serija)
        self["season"] = Label(season or "")
        self["episode"] = Label(episode or "")
        self["year"] = Label(year or "")
        self["language"] = Label("scc")  # Podrazumevano srpski
        self["status"] = Label("Enter search parameters and press GREEN to search")
        self["background"] = Pixmap()
        
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.doSearch,
                "yellow": self.openKeyboard,
                "blue": self.downloadCurrent,
                "up": self.moveUp,
                "down": self.moveDown,
                "left": self.moveLeft,
                "right": self.moveRight,
            },
            -1
        )
    
    def moveUp(self):
        """Pomeri se na gornji widget"""
        if self.current_widget_index > 0:
            self.current_widget_index -= 1
    
    def moveDown(self):
        """Pomeri se na donji widget"""
        if self.current_widget_index < len(self.widgets) - 1:
            self.current_widget_index += 1
    
    def moveLeft(self):
        """Pomeri se levo"""
        # Ako smo u episode, možemo da se vratimo u season
        if self.current_widget_index == 4:  # episode
            self.current_widget_index = 3  # season
        # Ako smo u season, možemo da se vratimo u type
        elif self.current_widget_index == 3:  # season
            self.current_widget_index = 2  # type
        # Ako smo u type, možemo da se vratimo u imdbid
        elif self.current_widget_index == 2:  # type
            self.current_widget_index = 1  # imdbid
    
    def moveRight(self):
        """Pomeri se desno"""
        # Ako smo u imdbid, možemo da pređemo u type
        if self.current_widget_index == 1:  # imdbid
            self.current_widget_index = 2  # type
        # Ako smo u type, možemo da pređemo u season
        elif self.current_widget_index == 2:  # type
            self.current_widget_index = 3  # season
        # Ako smo u season, možemo da pređemo u episode
        elif self.current_widget_index == 3:  # season
            self.current_widget_index = 4  # episode
    
    def getCurrentWidget(self):
        """Vraća naziv trenutnog widget-a"""
        if self.current_widget_index < len(self.widgets):
            return self.widgets[self.current_widget_index]
        return self.widgets[0]
    
    def openKeyboard(self):
        """Otvara virtuelnu tastaturu za trenutni widget"""
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()
        
        # Specijalni tretman za TYPE widget
        if current_widget == "type":
            # Umesto tastature, pokaži izbor tipa
            menu = [
                ("TV Series", "tv"),
                ("Movie", "movie"),
                ("Documentary", "documentary"),
                ("Anime", "anime"),
            ]
            
            self.session.openWithCallback(
                lambda choice: self.typeSelected(choice),
                ChoiceBox,
                title="Select media type",
                list=menu
            )
            return
        
        # Različiti naslovi za različite widget-e
        titles = {
            "searchtext": "Enter search text",
            "imdbid": "Enter IMDB ID (ttXXXXXXX)",
            "season": "Enter season number",
            "episode": "Enter episode number",
            "year": "Enter year",
            "language": "Enter language code (scc, en, etc.)"
        }
        
        title = titles.get(current_widget, f"Enter {current_widget}")
        
        self.session.openWithCallback(
            lambda text: self.keyboardCallback(text, current_widget),
            VirtualKeyBoard,
            title=title,
            text=current_text
        )
    
    def typeSelected(self, choice):
        """Callback nakon izbora tipa"""
        if choice:
            self["type"].setText(choice[1])
            # Automatski pređi na sledeći widget
            self.current_widget_index = 3  # Pređi na Season
    
    def keyboardCallback(self, text, widget_name):
        """Callback nakon unosa sa tastature"""
        if text is not None:
            self[widget_name].setText(text)
            
            # Auto-fokus na sledeći widget
            widget_index_map = {
                "searchtext": 1,    # Pređi na IMDB ID
                "imdbid": 2,        # Pređi na Type
                "type": 3,          # Pređi na Season
                "season": 4,        # Pređi na Episode
                "episode": 5,       # Pređi na Year
                "year": 6,          # Pređi na Language
                "language": 0       # Vrati se na Search text
            }
            
            if widget_name in widget_index_map:
                self.current_widget_index = widget_index_map[widget_name]
    
    def resetFields(self):
        """Resetuje sva polja"""
        self["searchtext"].setText("")
        self["imdbid"].setText("")
        self["type"].setText("tv")
        self["season"].setText("")
        self["episode"].setText("")
        self["year"].setText("")
        self["language"].setText("scc")
        self.current_widget_index = 0
        self["status"].setText("Fields reset")
    
    def doSearch(self):
        """Vrši pretragu"""
        search_text = self["searchtext"].getText().strip()
        imdb_id = self["imdbid"].getText().strip()
        media_type = self["type"].getText().strip()
        season = self["season"].getText().strip()
        episode = self["episode"].getText().strip()
        year = self["year"].getText().strip()
        language = self["language"].getText().strip()
        
        # Proveri da li je serija (ima season/episode)
        is_series = bool(season or episode)
        
        if not search_text and not imdb_id:
            self["status"].setText("Enter search text or IMDB ID")
            return
        
        self["status"].setText(f"Searching...")
        
        # Vrši pretragu u pozadini
        from enigma import eTimer
        self.search_timer = eTimer()
        self.search_timer.callback.append(
            lambda: self._performSearch(search_text, imdb_id, media_type, season, episode, year, language, is_series)
        )
        self.search_timer.start(300, True)

    # U SubtitlesAdvancedScreen._performSearch():
    def _performSearch(self, search_text, imdb_id, media_type, season, episode, year, language, is_series):
        """Vrši stvarnu pretragu"""
        try:
            # Ako je serija, koristi advanced search
            if is_series:
                # Kreiraj params kao u originalnom plugin-u
                params = {}

                # Dodaj IMDB ID ako postoji
                if imdb_id:
                    params['prevod'] = imdb_id
                elif search_text:
                    params['prevod'] = search_text

                # Dodaj advanced search parametre
                params['t'] = '2'  # Advanced search
                params['type'] = media_type or 'tv'
                params['sort'] = '4'  # Podrazumevano sortiranje

                # Dodaj sezonu/epizodu ako postoje
                if season:
                    params['s'] = season
                if episode:
                    params['e'] = episode

                # Koristi advanced search
                results = parse_subtitles_advanced(search_text, imdb_id, season, episode, year, language, params)
            else:
                # Ako je film, koristi basic search
                results = parse_subtitles_basic(search_text, year, language)

            # SAČUVAJ REZULTATE ZA DOWNLOAD
            self.last_search_results = results  # DODAJ OVO

            if not results:
                self["status"].setText(f"No results found")
                self.session.open(
                    MessageBox,
                    f"No subtitles found",
                    MessageBox.TYPE_INFO,
                    timeout=3
                )
                return

            # FIXED: Use SubtitlesResultsScreen instead of OpenSubtitlesResults
            self.session.open(SubtitlesResultsScreen, f"Subtitles: {search_text or imdb_id}", results)

        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Search error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def downloadCurrent(self):
        """Download trenutno selektovanog titla sa widget-a"""
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()

        # Za različite widget-e, radi različite stvari
        if current_widget == "searchtext":
            # Ako je searchtext, pretraži ponovo i download prvi rezultat
            self["status"].setText(f"Searching and downloading: {current_text}")
            self.searchAndDownload(current_text)

        elif current_widget == "language":
            # Jezik - samo informacija
            self["status"].setText(f"Selected language: {current_text}")

        elif current_widget == "year":
            # Godina - samo informacija
            self["status"].setText(f"Year: {current_text}")

        elif current_widget == "type":
            # Tip (film/serija) - samo informacija
            self["status"].setText(f"Type: {current_text}")

        elif current_widget in ["season", "episode", "imdbid"]:
            # Ostali parametri - pokaži download meni
            self.showDownloadMenu()

        else:
            # Default: pokaži download meni
            self.showDownloadMenu()

    def searchAndDownload(self, search_text):
        """Pretraži i download prvi rezultat"""
        # Koristi postojeće parametre sa forme
        if isinstance(self, SubtitlesBasicScreen):
            year = self["year"].getText()
            language = self["language"].getText()

            from enigma import eTimer
            self.search_timer = eTimer()
            self.search_timer.callback.append(
                lambda: self._searchAndDownloadBasic(search_text, year, language)
            )
            self.search_timer.start(300, True)

        elif isinstance(self, SubtitlesAdvancedScreen):
            imdb_id = self["imdbid"].getText()
            media_type = self["type"].getText()
            season = self["season"].getText()
            episode = self["episode"].getText()
            year = self["year"].getText()
            language = self["language"].getText()

            from enigma import eTimer
            self.search_timer = eTimer()
            self.search_timer.callback.append(
                lambda: self._searchAndDownloadAdvanced(search_text, imdb_id, media_type,
                                                        season, episode, year, language)
            )
            self.search_timer.start(300, True)

    def _searchAndDownloadAdvanced(self, search_text, imdb_id, media_type, season, episode, year, language):
        """Pretraži i download za Advanced screen"""
        try:
            # Proveri da li je serija (ima season/episode)
            is_series = bool(season or episode)

            if is_series:
                params = {}
                if imdb_id:
                    params['prevod'] = imdb_id
                elif search_text:
                    params['prevod'] = search_text

                params['t'] = '2'
                params['type'] = media_type or 'tv'
                params['sort'] = '4'

                if season:
                    params['s'] = season
                if episode:
                    params['e'] = episode

                results = parse_subtitles_advanced(search_text, imdb_id, season, episode, year, language, params)
            else:
                results = parse_subtitles_basic(search_text, year, language)

            if not results:
                self["status"].setText(f"No results found")
                self.session.open(
                    MessageBox,
                    f"No subtitles found",
                    MessageBox.TYPE_INFO,
                    timeout=3
                )
                return

            # Download prvi rezultat
            self.downloadSubtitle(results[0])

        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Search/download error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showDownloadMenu(self):
        """Prikaži meni za download opcije"""
        menu = []

        # Opcija 1: Download poslednje pronađene titlove
        if self.last_search_results:
            menu.append(("Download last search results", "download_last"))

        # Opcija 2: Download izabrani widget
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()
        if current_text and current_text not in ["scc", "tv", "movie"]:
            menu.append((f"Download using '{current_text}'", "download_current"))

        # Opcija 3: Pokreni novu pretragu
        menu.append(("Search and download", "search_download"))

        if menu:
            self.session.openWithCallback(
                self.downloadMenuCallback,
                ChoiceBox,
                title="Download Options",
                list=menu
            )
        else:
            self["status"].setText("No download options available")

    def downloadMenuCallback(self, choice):
        """Callback za download meni"""
        if not choice:
            return

        action = choice[1]

        if action == "download_last" and self.last_search_results:
            # Download prvi titl iz poslednjih rezultata
            self.downloadSubtitle(self.last_search_results[0])

        elif action == "download_current":
            # Download koristeći trenutni widget
            self.downloadCurrent()

        elif action == "search_download":
            # Pokreni ponovno pretragu
            if isinstance(self, SubtitlesBasicScreen):
                self.doSearch()
            elif isinstance(self, SubtitlesAdvancedScreen):
                self.doSearch()

    def downloadSubtitle(self, subtitle):
        """Download specifičan titl"""
        if not subtitle or not subtitle.get('url'):
            self["status"].setText("Invalid subtitle")
            return

        title = subtitle.get('title', 'Unknown')
        self["status"].setText(f"Downloading: {title}")

        # Koristi timer za background download
        from enigma import eTimer
        self.download_timer = eTimer()
        self.download_timer.callback.append(lambda: self._performDownload(subtitle))
        self.download_timer.start(300, True)

    def _performDownload(self, subtitle):
        """Vrši stvarni download"""
        try:
            url = subtitle.get('url')
            if not url:
                self["status"].setText("No download URL")
                return

            # Preuzmi titl
            filepath = download_subtitle(url)

            if filepath:
                filename = os.path.basename(filepath)
                self["status"].setText(f"Downloaded: {filename}")

                self.session.open(
                    MessageBox,
                    f"Subtitle successfully downloaded!\n\n"
                    f"File: {filename}\n"
                    f"Path: {filepath}\n\n"
                    f"The subtitle is now in your download folder.",
                    MessageBox.TYPE_INFO,
                    timeout=5
                )
            else:
                self["status"].setText("Download failed")
                self.session.open(
                    MessageBox,
                    "Failed to download subtitle. Please try again.",
                    MessageBox.TYPE_ERROR
                )

        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Download error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )


class SubtitlesResultsScreen(Screen):
    """Ekran za prikaz rezultata pretrage titlova"""

    skin = """
    <screen name="SubtitlesResultsScreen" position="center,center" size="1920,1080" title="Subtitles Results">
        <widget name="title" position="50,50" size="1820,60" font="Regular;36" foregroundColor="#FFD700" />
        
        <!-- LISTA REZULTATA -->
        <widget name="list" position="50,130" size="1820,750" 
                scrollbarMode="showOnDemand" font="Regular;28" itemHeight="40" />
        
        <!-- STATUS -->
        <widget name="status" position="50,890" size="1820,60" font="Regular;26" />
        
        <!-- FOOTER -->
        <eLabel position="0,980" size="1920,100" backgroundColor="#000000" zPosition="0" />
        
        <eLabel position="50,1000" size="300,50" font="Regular;26" foregroundColor="red" text="EXIT" />
        <eLabel position="400,1000" size="300,50" font="Regular;26" foregroundColor="green" text="GREEN - Download" />
        <eLabel position="800,1000" size="300,50" font="Regular;26" foregroundColor="yellow" text="YELLOW - Details" />
        <eLabel position="1200,1000" size="300,50" font="Regular;26" foregroundColor="blue" text="BLUE - Info" />
    </screen>
    """
    
    def __init__(self, session, title, results):
        Screen.__init__(self, session)
        
        self.results = results
        self["title"] = Label(title)
        self["list"] = MenuList([])
        self["status"] = Label(f"Found {len(results)} subtitles. Use UP/DOWN to navigate.")
        
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.downloadSubtitle,
                "yellow": self.showDetails,
                "blue": self.showInfo,
                "up": self.up,
                "down": self.down,
            },
            -1
        )
        
        self.onLayoutFinish.append(self.loadResults)
    
    def loadResults(self):
        """Učitava rezultate u listu"""
        display_list = []
        
        for i, subtitle in enumerate(self.results):
            title = subtitle.get('title', 'Unknown')
            language = subtitle.get('language', 'N/A')
            format_type = subtitle.get('format', 'N/A')
            
            # Skrati naslov ako je predugačak
            if len(title) > 100:
                title = title[:90] + "..."
            
            display_text = f"{i+1:2d}. {title} [{language}]"
            display_list.append(display_text)
        
        self["list"].setList(display_list)
    
    def getCurrentSubtitle(self):
        """Vraća trenutno selektovani titl"""
        idx = self["list"].getSelectedIndex()
        if idx < len(self.results):
            return self.results[idx]
        return None
    
    def downloadSubtitle(self):
        """Preuzima selektovani titl"""
        subtitle = self.getCurrentSubtitle()
        
        if not subtitle:
            self["status"].setText("No subtitle selected")
            return
        
        title = subtitle.get('title', 'Unknown')
        self["status"].setText(f"Downloading: {title}")
        
        from enigma import eTimer
        self.download_timer = eTimer()
        self.download_timer.callback.append(lambda: self._performDownload(subtitle))
        self.download_timer.start(300, True)
    
    def _performDownload(self, subtitle):
        """Vrši stvarno preuzimanje"""
        try:
            url = subtitle.get('url')
            if not url:
                self["status"].setText("No download URL")
                return
            
            # Preuzmi titl
            filepath = download_subtitle(url)
            
            if filepath:
                filename = os.path.basename(filepath)
                self["status"].setText(f"Downloaded: {filename}")
                
                self.session.open(
                    MessageBox,
                    f"Subtitle successfully downloaded!\n\n"
                    f"File: {filename}\n"
                    f"Path: {filepath}\n\n"
                    f"The subtitle is now in your download folder.",
                    MessageBox.TYPE_INFO,
                    timeout=5
                )
            else:
                self["status"].setText("Download failed")
                self.session.open(
                    MessageBox,
                    "Failed to download subtitle. Please try again.",
                    MessageBox.TYPE_ERROR
                )
        
        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            self.session.open(
                MessageBox,
                f"Download error:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )
    
    def showDetails(self):
        """Prikazuje detalje o titlu"""
        subtitle = self.getCurrentSubtitle()
        
        if not subtitle:
            return
        
        # Prikaži sve dostupne informacije
        details = []
        details.append(f"TITLE: {subtitle.get('title', 'N/A')}")
        details.append(f"LANGUAGE: {subtitle.get('language', 'N/A')}")
        details.append(f"FORMAT: {subtitle.get('format', 'N/A')}")
        details.append(f"DOWNLOADS: {subtitle.get('downloads', 'N/A')}")
        details.append(f"URL: {subtitle.get('url', 'N/A')}")
        
        if subtitle.get('fps'):
            details.append(f"FPS: {subtitle.get('fps')}")
        
        if subtitle.get('cd'):
            details.append(f"CD: {subtitle.get('cd')}")
        
        if subtitle.get('release'):
            details.append(f"RELEASE: {subtitle.get('release')}")
        
        if subtitle.get('uploader'):
            details.append(f"UPLOADER: {subtitle.get('uploader')}")
        
        if subtitle.get('size'):
            details.append(f"SIZE: {subtitle.get('size')}")
        
        if subtitle.get('date'):
            details.append(f"DATE: {subtitle.get('date')}")
        
        details_text = "\n".join(details)
        
        self.session.open(
            MessageBox,
            details_text,
            MessageBox.TYPE_INFO,
            timeout=10
        )
    
    def showInfo(self):
        """Prikazuje informacije o rezultatima"""
        info_text = f"Total results: {len(self.results)}\n\n"
        info_text += "Use GREEN to download subtitle\n"
        info_text += "Use YELLOW to view details\n"
        info_text += "Use BLUE to show this info\n"
        info_text += "Use EXIT to go back"
        
        self.session.open(
            MessageBox,
            info_text,
            MessageBox.TYPE_INFO,
            timeout=5
        )
    
    def up(self):
        """Pomeri se gore u listi"""
        self["list"].up()
    
    def down(self):
        """Pomeri se dole u listi"""
        self["list"].down()

class UniversalSearchScreen(Screen):
    """Univerzalna pretraga filmova i serija"""

    skin = """
    <screen name="UniversalSearchScreen" position="center,center" size="1920,1080" title="Pretraga Filmova">
        <!-- NASLOV -->
        <widget name="title" position="50,50" size="1820,70" font="Regular;38" halign="center" valign="center" foregroundColor="#FFD700" />

        <!-- LEVI PANEL SA FORMOM -->
        <eLabel position="50,150" size="900,750" backgroundColor="#1e1e1e" zPosition="-1" />

        <!-- DESNI PANEL SA STATUSOM -->
        <eLabel position="1000,150" size="870,750" backgroundColor="#151515" zPosition="-1" />

        <!-- FORMA ZA PRETRAGU -->
        <!-- TIP PRETRAGE (film/serija) -->
        <eLabel position="80,180" size="300,50" font="Regular;30" text="Tip pretrage:" foregroundColor="#05dffc" />
        <widget name="search_type" position="380,175" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- NAZIV FILMA/SERIJE -->
        <eLabel position="80,260" size="300,50" font="Regular;30" text="Naziv:" foregroundColor="#05dffc" />
        <widget name="search_name" position="380,255" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- OD GODINE -->
        <eLabel position="80,340" size="300,50" font="Regular;30" text="Od godine:" foregroundColor="#05dffc" />
        <widget name="year_from" position="380,335" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- DO GODINE -->
        <eLabel position="80,420" size="300,50" font="Regular;30" text="Do godine:" foregroundColor="#05dffc" />
        <widget name="year_to" position="380,415" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- ŽANR (opciono) -->
        <eLabel position="80,500" size="300,50" font="Regular;30" text="Žanr:" foregroundColor="#05dffc" />
        <widget name="genre" position="380,495" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- SORTIRANJE -->
        <eLabel position="80,580" size="300,50" font="Regular;30" text="Sortiranje:" foregroundColor="#05dffc" />
        <widget name="sort_by" position="380,575" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- IMDB ID (opciono) -->
        <eLabel position="80,660" size="300,50" font="Regular;30" text="IMDB ID:" foregroundColor="#05dffc" />
        <widget name="imdb_id" position="380,655" size="500,60" font="Regular;30" backgroundColor="#555555" />

        <!-- DESNI PANEL - STATUS I INSTRUKCIJE -->
        <eLabel position="1020,180" size="200,50" font="Regular;30" text="STATUS:" foregroundColor="#32CD32" />
        <widget name="status" position="1020,240" size="830,300" font="Regular;26" foregroundColor="white" />

        <eLabel position="1020,560" size="200,50" font="Regular;30" text="UPUTSTVO:" foregroundColor="#FFA500" />
        <eLabel position="1020,620" size="830,250" font="Regular;24" foregroundColor="#CCCCCC" text="Za pretragu nije obavezno popuniti sva polja!\n\nPrimeri:\n- Samo naziv (The Batman)\n- Samo godine (2023-2024)\n- Naziv + godine\n- Samo IMDB ID (tt1234567)\n\nPolja se automatski selektuju sa UP/DOWN.\nKorisite ŽUTO za tastaturu." />

        <!-- FOOTER SA DUGMADIMA -->
        <eLabel position="0,920" size="1920,160" backgroundColor="#000000" zPosition="0" />

        <eLabel position="50,940" size="300,50" font="Regular;28" foregroundColor="red" halign="center" valign="center" text="EXIT" />
        <eLabel position="400,940" size="300,50" font="Regular;28" foregroundColor="green" halign="center" valign="center" text="PRETRAŽI" />
        <eLabel position="750,940" size="300,50" font="Regular;28" foregroundColor="yellow" halign="center" valign="center" text="TASTATURA" />
        <eLabel position="1100,940" size="300,50" font="Regular;28" foregroundColor="blue" halign="center" valign="center" text="RESETUJ" />
        <eLabel position="1450,940" size="300,50" font="Regular;28" foregroundColor="white" halign="center" valign="center" text="INFO" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        # Lista widget-a (polja za unos) - redosled za navigaciju
        self.widgets = ["search_type", "search_name", "year_from", "year_to", "genre", "sort_by", "imdb_id"]
        self.current_widget_index = 0

        # Inicijalizuj widget-e sa podrazumevanim vrednostima
        self["title"] = Label("UNIVERZALNA PRETRAGA FILMOVA")
        self["search_type"] = Label("film")  # Podrazumevano: film
        self["search_name"] = Label("")
        self["year_from"] = Label("")
        self["year_to"] = Label("")
        self["genre"] = Label("")
        self["sort_by"] = Label("godini prikazivanja")  # Podrazumevano sortiranje
        self["imdb_id"] = Label("")
        self["status"] = Label("Popunite željena polja i pritisnite ZELENO za pretragu")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.performSearch,
                "yellow": self.openKeyboard,
                "blue": self.resetForm,
                "up": self.moveUp,
                "down": self.moveDown,
                "ok": self.openKeyboard,  # OK otvara tastaturu za trenutni widget
            },
            -1
        )

    def moveUp(self):
        """Pomeri se na prethodni widget"""
        if self.current_widget_index > 0:
            self.current_widget_index -= 1

    def moveDown(self):
        """Pomeri se na sledeći widget"""
        if self.current_widget_index < len(self.widgets) - 1:
            self.current_widget_index += 1

    def getCurrentWidget(self):
        """Vraća naziv trenutno selektovanog widget-a"""
        return self.widgets[self.current_widget_index]

    def openKeyboard(self):
        """Otvara virtuelnu tastaturu za trenutni widget"""
        current_widget = self.getCurrentWidget()
        current_text = self[current_widget].getText()

        # Specijalni tretman za search_type (tip pretrage)
        if current_widget == "search_type":
            menu = [
                ("Film", "film"),
                ("Serija", "serija"),
                ("Sve", "sve"),
            ]

            self.session.openWithCallback(
                lambda choice: self.typeSelected(choice),
                ChoiceBox,
                title="Izaberite tip pretrage",
                list=menu
            )
            return

        # Specijalni tretman za sort_by (sortiranje)
        elif current_widget == "sort_by":
            menu = [
                ("Po godini prikazivanja", "godini prikazivanja"),
                ("Po popularnosti", "popularnosti"),
                ("Po IMDb oceni", "imdb oceni"),
                ("Po korisničkoj oceni", "korisničkoj oceni"),
                ("Po naslovu (A-Z)", "naslovu a-z"),
                ("Po naslovu (Z-A)", "naslovu z-a"),
            ]

            self.session.openWithCallback(
                lambda choice: self.sortSelected(choice),
                ChoiceBox,
                title="Izaberite način sortiranja",
                list=menu
            )
            return

        # Specijalni tretman za genre (žanr)
        elif current_widget == "genre":
            menu = [
                ("Akcija", "akcija"),
                ("Avantura", "avantura"),
                ("Animirani", "animirani"),
                ("Biografski", "biografski"),
                ("Komedija", "komedija"),
                ("Kriminalistički", "kriminalistički"),
                ("Dokumentarni", "dokumentarni"),
                ("Drama", "drama"),
                ("Porodični", "porodični"),
                ("Fantazija", "fantazija"),
                ("Istorijski", "istorijski"),
                ("Horor", "horor"),
                ("Misterija", "misterija"),
                ("Romantika", "romantika"),
                ("Naučna fantastika", "naučna fantastika"),
                ("Sport", "sport"),
                ("Triler", "triler"),
                ("Ratni", "ratni"),
                ("Vestern", "vestern"),
            ]

            self.session.openWithCallback(
                lambda choice: self.genreSelected(choice),
                ChoiceBox,
                title="Izaberite žanr",
                list=menu
            )
            return

        # Za ostala polja koristi standardnu tastaturu
        titles = {
            "search_name": "Unesite naziv filma/serije",
            "year_from": "Unesite početnu godinu",
            "year_to": "Unesite krajnju godinu",
            "imdb_id": "Unesite IMDB ID (npr. tt1234567)",
        }

        title = titles.get(current_widget, f"Unesite {current_widget}")

        self.session.openWithCallback(
            lambda text: self.keyboardCallback(text, current_widget),
            VirtualKeyBoard,
            title=title,
            text=current_text
        )

    def typeSelected(self, choice):
        """Callback nakon izbora tipa pretrage"""
        if choice:
            self["search_type"].setText(choice[1])
            # Automatski pređi na sledeći widget
            self.current_widget_index = 1  # Pređi na Naziv

    def sortSelected(self, choice):
        """Callback nakon izbora sortiranja"""
        if choice:
            self["sort_by"].setText(choice[1])
            # Automatski pređi na sledeći widget
            self.current_widget_index = 6  # Pređi na IMDB ID

    def genreSelected(self, choice):
        """Callback nakon izbora žanra"""
        if choice:
            self["genre"].setText(choice[1])
            # Automatski pređi na sledeći widget
            self.current_widget_index = 5  # Pređi na Sortiranje

    def keyboardCallback(self, text, widget_name):
        """Callback nakon unosa sa tastature"""
        if text is not None:
            self[widget_name].setText(text)

            # Auto-fokus na sledeći widget
            widget_index_map = {
                "search_name": 2,  # Pređi na Od godine
                "year_from": 3,  # Pređi na Do godine
                "year_to": 4,  # Pređi na Žanr
                "imdb_id": 0  # Vrati se na Tip pretrage
            }

            if widget_name in widget_index_map:
                self.current_widget_index = widget_index_map[widget_name]

    def resetForm(self):
        """Resetuje sva polja na podrazumevane vrednosti"""
        self["search_type"].setText("film")
        self["search_name"].setText("")
        self["year_from"].setText("")
        self["year_to"].setText("")
        self["genre"].setText("")
        self["sort_by"].setText("godini prikazivanja")
        self["imdb_id"].setText("")
        self.current_widget_index = 0
        self["status"].setText("Forma resetovana. Popunite polja i pritisnite ZELENO.")

    def performSearch(self):
        """Vrši pretragu sa unetim parametrima"""
        # Prikupi sve parametre
        search_type = self["search_type"].getText().strip().lower()
        search_name = self["search_name"].getText().strip()
        year_from = self["year_from"].getText().strip()
        year_to = self["year_to"].getText().strip()
        genre = self["genre"].getText().strip()
        sort_by = self["sort_by"].getText().strip()
        imdb_id = self["imdb_id"].getText().strip()

        # Provera da li je bar nešto uneto
        if not any([search_name, year_from, year_to, imdb_id]):
            self["status"].setText("GREŠKA: Unesite bar jedan parametar za pretragu!\n(Naziv, godine ili IMDB ID)")
            self.session.open(
                MessageBox,
                "Morate uneti bar jedan parametar za pretragu:\n- Naziv filma/serije\n- Godine\n- IMDB ID",
                MessageBox.TYPE_ERROR,
                timeout=5
            )
            return

        # Provera godina
        if year_from and not year_from.isdigit():
            self["status"].setText(f"GREŠKA: 'Od godine' mora biti broj!\nUneli ste: {year_from}")
            return

        if year_to and not year_to.isdigit():
            self["status"].setText(f"GREŠKA: 'Do godine' mora biti broj!\nUneli ste: {year_to}")
            return

        # Pripremi status poruku
        status_msg = "Pretražujem..."
        if search_name:
            status_msg += f"\nNaziv: {search_name}"
        if year_from or year_to:
            status_msg += f"\nGodine: {year_from if year_from else '?'} - {year_to if year_to else '?'}"
        if genre:
            status_msg += f"\nŽanr: {genre}"
        if imdb_id:
            status_msg += f"\nIMDB ID: {imdb_id}"

        self["status"].setText(status_msg)

        # Pokreni pretragu u pozadini
        from enigma import eTimer
        self.search_timer = eTimer()
        self.search_timer.callback.append(
            lambda: self._performSearchNow(search_type, search_name, year_from, year_to, genre, sort_by, imdb_id)
        )
        self.search_timer.start(300, True)

    def _performSearchNow(self, search_type, search_name, year_from, year_to, genre, sort_by, imdb_id):
        """Vrši stvarnu pretragu - KORISTI PRAVU universal_search FUNKCIJU"""
        try:
            # Pripremi parametre za universal_search
            search_params = {
                'type': search_type,
                'name': search_name,
                'year_from': year_from,
                'year_to': year_to,
                'genre': genre,
                'sort': sort_by,
                'imdb_id': imdb_id
            }

            # Prikaži status
            status_msg = "Pretražujem..."
            if search_name:
                status_msg += f"\nNaziv: {search_name}"
            if year_from or year_to:
                status_msg += f"\nGodine: {year_from if year_from else '?'}-{year_to if year_to else '?'}"
            if genre:
                status_msg += f"\nŽanr: {genre}"
            if imdb_id:
                status_msg += f"\nIMDB ID: {imdb_id}"

            self["status"].setText(status_msg)

            # Pokreni pretragu u pozadini
            from enigma import eTimer
            self.search_timer = eTimer()
            self.search_timer.callback.append(
                lambda: self._executeUniversalSearch(search_params)
            )
            self.search_timer.start(500, True)

        except Exception as e:
            self["status"].setText(f"Greška pri pokretanju pretrage: {str(e)[:100]}")
            self.session.open(
                MessageBox,
                f"Greška pri pokretanju pretrage:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def _executeUniversalSearch(self, search_params):
        """Izvršava universal_search i obrađuje rezultate"""
        try:
            # Koristi universal_search iz parser.py
            results = universal_search(search_params)

            if not results:
                # Pokazujemo šta je traženo
                search_type = search_params.get('type', 'sve')
                search_name = search_params.get('name', '')

                msg = f"Nema rezultata za pretragu"
                if search_type != 'sve':
                    msg += f" tipa: {search_type}"
                if search_name:
                    msg += f"\nNaziv: '{search_name}'"
                if search_params.get('year_from') or search_params.get('year_to'):
                    year_from = search_params.get('year_from', '?')
                    year_to = search_params.get('year_to', '?')
                    msg += f"\nGodine: {year_from}-{year_to}"

                self["status"].setText("Nema rezultata")
                self.session.open(
                    MessageBox,
                    msg,
                    MessageBox.TYPE_INFO,
                    timeout=5
                )
                return

            # Razdvoji filmove i serije
            movies = []
            series = []

            for item in results:
                item_type = item.get('type', '').lower()
                if item_type == 'film':
                    movies.append(item)
                elif item_type == 'series':
                    series.append(item)
                else:
                    # Ako ne možemo da odredimo, proveri URL
                    url = item.get('url', '').lower()
                    if '/serije/' in url:
                        series.append(item)
                    elif '/filmovi/' in url:
                        movies.append(item)
                    else:
                        # Podrazumevano stavi u obe liste
                        movies.append(item)
                        series.append(item)

            # Pripremi naslov
            title_parts = []
            search_type = search_params.get('type', 'sve')

            if search_type != 'sve':
                title_parts.append(f"Tip: {search_type}")

            search_name = search_params.get('name', '')
            if search_name:
                title_parts.append(f"'{search_name}'")

            year_from = search_params.get('year_from', '')
            year_to = search_params.get('year_to', '')
            if year_from or year_to:
                year_range = f"{year_from if year_from else '?'}-{year_to if year_to else '?'}"
                title_parts.append(year_range)

            genre = search_params.get('genre', '')
            if genre:
                title_parts.append(genre)

            # Pokaži meni sa rezultatima
            self._showResultsMenu(movies, series, title_parts, search_type, len(results))

        except Exception as e:
            self["status"].setText(f"Greška pri pretrazi: {str(e)[:100]}")
            self.session.open(
                MessageBox,
                f"Greška pri pretrazi:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def _showResultsMenu(self, movies, series, title_parts, search_type, total_count):
        """Prikazuje meni sa rezultatima"""
        # Kreiraj osnovni naslov
        if title_parts:
            base_title = f"Pretraga: {' | '.join(title_parts)}"
        else:
            base_title = "Rezultati pretrage"

        base_title = f"{base_title} ({total_count})"

        menu_items = []

        # Opcija za filmove
        if movies:
            movie_title = "Filmovi"
            if search_type == 'film':
                movie_title = f"🎬 Filmovi ({len(movies)})"
            else:
                movie_title = f"🎬 Prikaži filmove ({len(movies)})"

            menu_items.append((movie_title, ("movies", movies, f"{base_title} - Filmovi")))

        # Opcija za serije
        if series:
            series_title = "Serije"
            if search_type == 'serija':
                series_title = f"📺 Serije ({len(series)})"
            else:
                series_title = f"📺 Prikaži serije ({len(series)})"

            menu_items.append((series_title, ("series", series, f"{base_title} - Serije")))

        # Opcija za sve zajedno (samo ako ima oba tipa i tražili smo "sve")
        if movies and series and search_type == 'sve':
            menu_items.append((f"🎬📺 Svi rezultati ({total_count})",
                               ("all", movies + series, base_title)))

        # Ako nema rezultata, prikaži poruku
        if not menu_items:
            self["status"].setText("Nema rezultata za prikaz")
            return

        # Dodaj opciju za nazad
        menu_items.append(("🔙 Nazad", "back"))

        self.session.openWithCallback(
            lambda choice: self._resultsMenuCallback(choice),
            ChoiceBox,
            title=base_title,
            list=menu_items
        )

    def _resultsMenuCallback(self, choice):
        """Callback za meni rezultata"""
        if not choice or choice[1] == "back":
            return

        result_type, items, title = choice[1]

        if result_type == "movies":
            self.session.open(MovieListScreen, title, items)
        elif result_type == "series":
            self.session.open(SeriesSearchScreen, title, items)
        elif result_type == "all":
            self.session.open(MovieListScreen, title, items)

    def _sort_results(self, results, sort_by):
        """Sortira rezultate prema izboru"""
        if not results or sort_by == 'popularnosti':
            return results

        try:
            if sort_by == 'godini prikazivanja':
                # Sortiraj po godini (najnovije prvo)
                return sorted(results,
                              key=lambda x: int(x.get('year', 0)) if x.get('year', 'N/A').isdigit() else 0,
                              reverse=True)
            elif sort_by == 'naslovu a-z':
                # Sortiraj po naslovu A-Z
                return sorted(results,
                              key=lambda x: x.get('title', '').lower())
            elif sort_by == 'naslovu z-a':
                # Sortiraj po naslovu Z-A
                return sorted(results,
                              key=lambda x: x.get('title', '').lower(),
                              reverse=True)
            else:
                return results
        except:
            return results

    def _search_by_imdb(self, imdb_id, search_type):
        """Pretražuje po IMDB ID-u"""
        # Koristi search_movies i search_series sa IMDB ID kao upit
        results = []

        try:
            # Pokušaj da nađeš film
            if search_type == "film" or search_type == "sve":
                movie_results = search_movies(f"tt{imdb_id}" if not imdb_id.startswith('tt') else imdb_id)
                if movie_results:
                    results.extend(movie_results)

            # Pokušaj da nađeš seriju
            if search_type == "serija" or search_type == "sve":
                series_results = search_series(f"tt{imdb_id}" if not imdb_id.startswith('tt') else imdb_id)
                if series_results:
                    results.extend(series_results)

        except:
            pass

        return results

    def _filter_by_years(self, items, year_from, year_to):
        """Filtrira rezultate po godinama"""
        filtered = []

        for item in items:
            try:
                item_year = item.get('year', 'N/A')

                # Ako nema godine, preskoči
                if item_year == 'N/A' or not item_year.isdigit():
                    continue

                year_int = int(item_year)

                # Proveri uslove
                from_ok = True
                to_ok = True

                if year_from and year_from.isdigit():
                    from_ok = year_int >= int(year_from)

                if year_to and year_to.isdigit():
                    to_ok = year_int <= int(year_to)

                if from_ok and to_ok:
                    filtered.append(item)

            except:
                continue

        return filtered

    def _filter_by_genre(self, items, genre):
        """Filtrira rezultate po žanru"""
        # Ovo će biti preciznije kada parser vraća i žanrove
        # Za sada vraćamo sve
        return items

    def _search_by_years(self, year_from, year_to, search_type):
        """Pretražuje samo po godinama"""
        results = []

        try:
            # Za sada koristimo parse_all_movies i parse_all_series
            # Ovo može biti sporo, ali radi za demo

            if search_type == "film" or search_type == "sve":
                # Parsiraj filmove i filtriraj
                movies_data = parse_all_movies(1, 50)  # Prvih 50 filmova
                movies = movies_data.get('items', [])

                filtered_movies = self._filter_by_years(movies, year_from, year_to)
                results.extend(filtered_movies)

            if search_type == "serija" or search_type == "sve":
                # Parsiraj serije i filtriraj
                series_data = parse_all_series(1, 50)  # Prvih 50 serija
                series = series_data.get('items', [])

                filtered_series = self._filter_by_years(series, year_from, year_to)
                results.extend(filtered_series)

        except Exception as e:
            print(f"DEBUG: Error in year search: {e}")

        return results

    def _show_results(self, results, title_prefix):
        """Prikazuje rezultate pretrage"""
        if not results:
            return

        # Kreiraj naslov sa brojem rezultata
        title = f"Rezultati: {title_prefix} ({len(results)})"

        # Pripremi rezultate za MovieListScreen
        formatted_results = []
        for item in results:
            # Dodaj godinu u prikaz ako postoji
            display_item = item.copy()
            year = item.get('year', '')
            if year and year != 'N/A':
                display_item['title'] = f"{item.get('title', '')} ({year})"

            formatted_results.append(display_item)

        # Koristi postojeći MovieListScreen za prikaz
        self.session.open(MovieListScreen, title, formatted_results)

    def _search_movies(self, search_name, year_from, year_to, imdb_id):
        """Pomoćna funkcija za pretragu filmova"""
        try:
            # Prvo pokušaj sa search_movies ako postoji funkcija
            if search_name and hasattr(self, 'search_movies'):
                return search_movies(search_name)

            # Ako nema rezultata, pokušaj sa parse_all_movies i filter
            all_movies = parse_all_movies(1, 100)  # Uzmi prviih 100
            movies = all_movies.get("items", [])

            # Filtriraj po parametrima
            filtered = []
            for movie in movies:
                matches = True

                # Filter po nazivu
                if search_name:
                    movie_title = movie.get("title", "").lower()
                    if search_name.lower() not in movie_title:
                        matches = False

                # Filter po godini
                if year_from:
                    movie_year = movie.get("year", "")
                    if movie_year.isdigit() and int(movie_year) < int(year_from):
                        matches = False

                if year_to:
                    movie_year = movie.get("year", "")
                    if movie_year.isdigit() and int(movie_year) > int(year_to):
                        matches = False

                if matches:
                    filtered.append(movie)

            return filtered

        except Exception as e:
            print(f"DEBUG: Error in movie search: {e}")
            return []

    def _search_series(self, search_name, year_from, year_to, imdb_id):
        """Pomoćna funkcija za pretragu serija"""
        try:
            # Prvo pokušaj sa search_series ako postoji funkcija
            if search_name and hasattr(self, 'search_series'):
                return search_series(search_name)

            # Ako nema rezultata, pokušaj sa parse_all_series i filter
            all_series = parse_all_series(1, 100)  # Uzmi prviih 100
            series = all_series.get("items", [])

            # Filtriraj po parametrima
            filtered = []
            for s in series:
                matches = True

                # Filter po nazivu
                if search_name:
                    series_title = s.get("title", "").lower()
                    if search_name.lower() not in series_title:
                        matches = False

                # Filter po godini
                if year_from:
                    series_year = s.get("year", "")
                    if series_year.isdigit() and int(series_year) < int(year_from):
                        matches = False

                if year_to:
                    series_year = s.get("year", "")
                    if series_year.isdigit() and int(series_year) > int(year_to):
                        matches = False

                if matches:
                    filtered.append(s)

            return filtered

        except Exception as e:
            print(f"DEBUG: Error in series search: {e}")
            return []

class TitloviConfigScreen(ConfigListScreen, Screen):
    skin = """
    <screen name="TitloviConfigScreen" position="center,center" size="1920,1080" title="Titlovi Browser Configuration">
        <!-- BACKGROUND -->
        <eLabel position="0,0" size="1920,1080" backgroundColor="#1e1e1e" zPosition="-2" />
        
        <!-- NASLOV -->
        <widget name="config" position="100,100" size="1200,800" 
                scrollbarMode="showOnDemand" itemHeight="45" enableWrapAround="1" />
        
        <!-- BACKGROUND -->
        <widget name="background" position="1300,100" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />
        
        <!-- FOOTER -->
        <eLabel position="0,920" size="1920,160" backgroundColor="#000000" zPosition="-1" />
        
        <eLabel position="50,940" size="300,50" font="Regular;28" foregroundColor="red" halign="center" valign="center" text="EXIT" />
        <eLabel position="400,940" size="300,50" font="Regular;28" foregroundColor="green" halign="center" valign="center" text="GREEN - Save" />
        <eLabel position="750,940" size="300,50" font="Regular;28" foregroundColor="yellow" halign="center" valign="center" text="YELLOW - Default" />
        <eLabel position="1100,940" size="300,50" font="Regular;28" foregroundColor="blue" halign="center" valign="center" text="BLUE - Test Path" />
    </screen>
    """ % BACKGROUND
    
    def __init__(self, session):
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [], session=session)
        
        # Inicijalizuj konfiguraciju
        self.initConfig()
        
        # Kreiraj config listu
        self["config"].list = self.getConfigList()
        
        self["background"] = Pixmap()
        
        # ActionMap
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "cancel": self.cancel,
                "red": self.cancel,
                "green": self.save,
                "yellow": self.setDefaults,
                "blue": self.testDownloadPath,
                "ok": self.save,
            },
            -1
        )
        
        self.setTitle("Titlovi Browser Configuration")
    
    def initConfig(self):
        """Inicijalizuje config objekte"""
        # DOWNLOAD PATH
        default_path = "/media/hdd/subtitles/"
        self.download_path = ConfigText(default=default_path, fixed_size=False)
        
        # DEFAULT LANGUAGE
        language_choices = [
            ("srpski (srp)", "srp"),
            ("hrvatski (hrv)", "hrv"),
            ("bosanski (bos)", "bos"),
            ("slovenački (slv)", "slv"),
            ("makedonski (mkd)", "mkd"),
            ("engleski (eng)", "eng"),
            ("svi jezici", "all")
        ]
        self.default_language = ConfigSelection(default="srp", choices=language_choices)
        
        # CACHE SIZE LIMIT
        cache_choices = [
            ("20 MB", "20"),
            ("40 MB", "40"),
            ("60 MB", "60"),
            ("80 MB", "80"),
            ("100 MB", "100"),
            ("200 MB", "200"),
            ("Bez ograničenja", "0")
        ]
        self.cache_limit = ConfigSelection(default="20", choices=cache_choices)
        
        # AUTO CLEAR CACHE
        self.auto_clear_cache = ConfigYesNo(default=False)
        
        # ENABLE DEBUG LOGGING
        self.enable_debug = ConfigYesNo(default=False)
        
        # DEFAULT SEARCH TYPE
        search_choices = [
            ("Basic (naziv)", "basic"),
            ("Advanced (IMDB, sezona)", "advanced"),
            ("Auto detect", "auto")
        ]
        self.default_search = ConfigSelection(default="auto", choices=search_choices)
    
    def getConfigList(self):
        """Kreira listu config stavki"""
        return [
            getConfigListEntry("📂 Download putanja:", self.download_path),
            getConfigListEntry("🌐 Podrazumevani jezik:", self.default_language),
            getConfigListEntry("🔍 Podrazumevana pretraga:", self.default_search),
            getConfigListEntry("💾 Limit keš memorije (MB):", self.cache_limit),
            getConfigListEntry("🗑️ Automatsko brisanje keša:", self.auto_clear_cache),
            getConfigListEntry("🐛 Debug logovanje:", self.enable_debug)
        ]

    def save(self):
        """Sačuvaj podešavanja"""
        # Sačuvaj u config
        config.plugins.titlovibrowser.downloadpath.value = self.download_path.value.strip()
        config.plugins.titlovibrowser.downloadpath.save()

        # Proveri download path
        download_path = config.plugins.titlovibrowser.downloadpath.value
        if download_path and not download_path.endswith('/'):
            download_path += '/'
            config.plugins.titlovibrowser.downloadpath.value = download_path
            config.plugins.titlovibrowser.downloadpath.save()

        # Kreiraj folder ako ne postoji
        if download_path:
            try:
                os.makedirs(download_path, exist_ok=True)
            except:
                pass

        self.session.open(
            MessageBox,
            "Podešavanja su sačuvana!",
            MessageBox.TYPE_INFO,
            timeout=3
        )
        self.close()

    def cancel(self):
        """Izlaz bez čuvanja"""
        self.close()
    
    def setDefaults(self):
        """Resetuj na podrazumevane vrednosti"""
        self.session.openWithCallback(
            self.confirmDefaults,
            MessageBox,
            "Da li želite da resetujete sva podešavanja\nna podrazumevane vrednosti?",
            MessageBox.TYPE_YESNO
        )
    
    def confirmDefaults(self, result):
        if result:
            self.download_path.setValue("/media/hdd/subtitles/")
            self.default_language.setValue("srp")
            self.default_search.setValue("auto")
            self.cache_limit.setValue("500")
            self.auto_clear_cache.setValue(False)
            self.enable_debug.setValue(False)
            
            # Refresh list
            self["config"].list = self.getConfigList()
            self["config"].l.setList(self["config"].list)
    
    def testDownloadPath(self):
        """Testira download path"""
        path = self.download_path.value.strip()
        if not path:
            self.session.open(
                MessageBox,
                "Download putanja nije postavljena!",
                MessageBox.TYPE_ERROR
            )
            return
        
        try:
            # Proveri da li folder postoji
            exists = os.path.exists(path)
            
            # Proveri da li je upisivo
            writable = os.access(path, os.W_OK) if exists else False
            
            # Pokušaj da kreiraš ako ne postoji
            if not exists:
                os.makedirs(path, exist_ok=True)
                exists = os.path.exists(path)
                writable = os.access(path, os.W_OK)
            
            msg = f"Download putanja:\n{path}\n\n"
            msg += f"Status: {'POSTOJI' if exists else 'NE POSTOJI'}\n"
            msg += f"Upisiv: {'DA' if writable else 'NE'}"
            
            if exists and writable:
                mtype = MessageBox.TYPE_INFO
            else:
                mtype = MessageBox.TYPE_ERROR
            
            self.session.open(
                MessageBox,
                msg,
                mtype,
                timeout=5
            )
            
        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška prilikom testiranja putanje:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )        
# Dodaj u plugin.py (može biti globalna funkcija ili metoda u glavnoj klasi)

def clear_cache():
    """Briše sav cache iz /tmp/Titlovi_Browser"""
    import shutil
    cache_dir = "/tmp/Titlovi_Browser"
    
    if os.path.exists(cache_dir):
        try:
            # Obriši ceo folder
            shutil.rmtree(cache_dir)
            
            # Ponovo kreiraj prazan
            os.makedirs(cache_dir, exist_ok=True)
            
            return True, f"Cache uspešno obrisan!\n\n{get_cache_size()}"
            
        except Exception as e:
            return False, f"Greška pri brisanju cache-a:\n{str(e)}"
    else:
        return True, "Cache folder ne postoji."


class SubtitleFileExplorer(Screen):
    """File Explorer za pregled skinutih titlova"""

    skin = """
    <screen position="center,center" size="1920,1080" title="Subtitle File Explorer" backgroundColor="#000000">
        <eLabel position="0,0" size="1600,800" backgroundColor="#000000" zPosition="-10" />

        <widget name="header" position="50,100" size="1100,50" font="Regular;32" 
                foregroundColor="#ffff00" halign="center" valign="center" />

        <widget name="path_label" position="50,160" size="150,40" 
                font="Regular;28" foregroundColor="#ffffff" valign="center" />
        <widget name="path" position="210,160" size="900,40" 
                font="Regular;28" foregroundColor="#ffff00" />

        <widget name="files" position="50,210" size="1200,700" enableWrapAround="1" 
                scrollbarMode="showOnDemand" backgroundColor="#111111" foregroundColor="#ffffff" 
                itemHeight="45" font="Regular;24" />

        <widget name="status" position="60,950" size="1100,40" 
                font="Regular;26" foregroundColor="#ffff00" transparent="1" />
                
        <!-- BACKGROUND -->
        <widget name="background" position="1300,100" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />
        
        <!-- Dugmad -->
        <eLabel text="Exit" position="50,1000" size="200,50" font="Regular;26" 
                foregroundColor="#ffffff" backgroundColor="#9f1313" halign="center" valign="center" />
        <eLabel text="Select" position="280,1000" size="200,50" font="Regular;26" 
                foregroundColor="#ffffff" backgroundColor="#1f771f" halign="center" valign="center" />
        <eLabel text="Delete" position="510,1000" size="200,50" font="Regular;26" 
                foregroundColor="#ffffff" backgroundColor="#a08500" halign="center" valign="center" />
        <eLabel text="Multi Select" position="740,1000" size="200,50" font="Regular;26" 
                foregroundColor="#ffffff" backgroundColor="#18188b" halign="center" valign="center" />
    </screen>
    """ % BACKGROUND

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self["header"] = Label("SUBTITLE FILE EXPLORER")
        self["path_label"] = Label("Path:")
        self["path"] = Label("")
        self["status"] = Label("Loading files...")
        self["background"] = Pixmap()

        self["files"] = MenuList([])
        self.file_list = []  # Lista fajlova sa punim putevima
        self.current_dir = ""
        self.selected_files = set()  # NOVO: set za multi-selection
        self.multi_select_mode = False  # NOVO: mod za višestruko selekciju
        self["actions"] = ActionMap(["ColorActions", "SetupActions", "MovieSelectionActions"],
                                    {
                                        "red": self.close,
                                        "green": self.selectFile,
                                        "yellow": self.deleteFile,
                                        "blue": self.toggleMultiSelect,  # NOVO
                                        "cancel": self.close,
                                        "ok": self.toggleSelection,  # PROMENJENO
                                        "up": self.up,
                                        "down": self.down,
                                        "left": self.left,
                                        "right": self.right,
                                    }, -2)

        self.onLayoutFinish.append(self.loadFiles)

    def loadFiles(self):
        """Učitaj fajlove iz config foldera"""
        save_path = get_download_path()
        self.current_dir = save_path

        # Proveri da li folder postoji
        if not pathExists(save_path):
            self["status"].setText("Folder does not exist!")
            self["path"].setText(save_path)
            self.updateFileListDisplay()
            return

        self["path"].setText(save_path)
        self["status"].setText("Loading...")

        try:
            import os
            from datetime import datetime

            # Pronađi sve subtitle fajlove
            subtitle_extensions = ['.srt', '.sub', '.ass', '.ssa', '.vtt', '.txt']

            # Resetuj listu
            self.file_list = []

            for filename in sorted(os.listdir(save_path), key=lambda x: os.path.getmtime(os.path.join(save_path, x)),
                                   reverse=True):
                full_path = os.path.join(save_path, filename)

                # Proveri da li je fajl (ne folder) i da li je subtitle
                if os.path.isfile(full_path):
                    if any(filename.lower().endswith(ext) for ext in subtitle_extensions):
                        # Dobij informacije o fajlu
                        file_size = os.path.getsize(full_path)
                        mod_time = os.path.getmtime(full_path)
                        mod_date = datetime.fromtimestamp(mod_time).strftime('%d.%m.%Y %H:%M')

                        self.file_list.append({
                            'path': full_path,
                            'name': filename,
                            'size': file_size,
                            'date': mod_date
                        })

            # Uvek osvežavamo prikaz preko jedinstvene funkcije
            self.updateFileListDisplay()

            if self.file_list:
                self["status"].setText(f"Found {len(self.file_list)} subtitle files")
            else:
                self["status"].setText("No subtitle files in folder")

        except Exception as e:
            print(f"[FILE EXPLORER] Error loading files: {e}")
            self["status"].setText(f"Error: {str(e)[:50]}")
            self.file_list = []
            self.updateFileListDisplay()

    def selectFile(self):
        """Selektuj fajl za dodatne opcije"""
        selected_idx = self["files"].getSelectedIndex()

        if not self.file_list or selected_idx >= len(self.file_list):
            self["status"].setText("No file selected!")
            return

        file_info = self.file_list[selected_idx]
        filename = file_info['name']

        # Prikaži opcije za fajl
        options = [
            (f"Delete '{filename}'", "delete"),
            (f"Rename file", "rename"),
            (f"View file info", "info"),
            ("Cancel", "cancel")
        ]

        self.session.openWithCallback(
            self.fileActionCallback,
            ChoiceBox,
            title=f"File: {filename}",
            list=options
        )

    def fileActionCallback(self, result):
        """Callback za akcije nad fajlom"""
        if result is None:
            return

        action, action_type = result

        if action_type == "delete":
            self.deleteFile()
        elif action_type == "rename":
            self.renameFile()
        elif action_type == "info":
            self.showFileInfo()

    def toggleMultiSelect(self):
        """Uključi/isključi multi-selection mode"""
        self.multi_select_mode = not self.multi_select_mode

        if self.multi_select_mode:
            self["status"].setText("MULTI-SELECT: ON (OK=select, BLUE=delete all)")
            self.selected_files.clear()
        else:
            self["status"].setText("MULTI-SELECT: OFF")
            self.selected_files.clear()

        self.updateFileListDisplay()

    def toggleSelection(self):
        """Selektuj/odselektuj fajl u multi-selection modu"""
        selected_idx = self["files"].getSelectedIndex()

        if not self.file_list or selected_idx >= len(self.file_list):
            return

        if self.multi_select_mode:
            file_path = self.file_list[selected_idx]['path']

            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
            else:
                self.selected_files.add(file_path)

            self.updateFileListDisplay()

            # Prikaži broj selektovanih fajlova
            selected_count = len(self.selected_files)
            self["status"].setText(f"Multi-select: {selected_count} files selected")
        else:
            # Originalno ponašanje - prikaži opcije
            self.selectFile()

    def updateFileListDisplay(self):
        """Ažuriraj prikaz fajlova sa selektovanim oznakama"""
        list_items = []

        for idx, file_info in enumerate(self.file_list):
            filename = file_info['name']
            display_name = filename
            if len(filename) > 80:
                name, ext = os.path.splitext(filename)
                display_name = name[:37] + "..." + ext

            # Dodaj oznaku za selektovane fajlove
            prefix = ""
            if self.multi_select_mode:
                if file_info['path'] in self.selected_files:
                    prefix = "✓ "  # Checkmark za selektovano
                else:
                    prefix = "  "  # Prazno mesto

            # Formatiraj prikaz
            display_text = f"{prefix}{display_name}"
            display_text += f" ({self.format_size(file_info['size'])}, {file_info['date']})"

            list_items.append(display_text)

        self["files"].setList(list_items)

    def confirmMultiDelete(self, confirmed):
        """Potvrdi brisanje više fajlova"""
        if not confirmed:
            self["status"].setText("Multi-delete cancelled")
            return

        deleted_count = 0
        errors = []

        for file_path in list(self.selected_files):
            try:
                import os
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1

                    # Ukloni iz file_list
                    self.file_list = [f for f in self.file_list if f['path'] != file_path]
            except Exception as e:
                errors.append(f"Error deleting {os.path.basename(file_path)}: {str(e)[:30]}")

        # Resetuj selektciju
        self.selected_files.clear()
        self.multi_select_mode = False

        # Refresh prikaz
        self.refreshFiles()

        # Prikaži rezultat
        if deleted_count > 0:
            self["status"].setText(f"Deleted {deleted_count} files")

            msg = f"Successfully deleted {deleted_count} file(s)"
            if errors:
                msg += f"\n\nErrors: {len(errors)} file(s) failed"
                for error in errors[:3]:
                    msg += f"\n• {error}"
                if len(errors) > 3:
                    msg += f"\n• ... and {len(errors) - 3} more"

            self.session.open(
                MessageBox,
                msg,
                MessageBox.TYPE_INFO if not errors else MessageBox.TYPE_WARNING,
                timeout=5
            )
        else:
            self["status"].setText("No files deleted")

    def deleteFile(self):
        """Obriši fajl/fajlove - podržava multi-selection"""
        if self.multi_select_mode and self.selected_files:
            # Brisanje više fajlova
            selected_count = len(self.selected_files)

            # Potvrda
            self.session.openWithCallback(
                lambda confirm: self.confirmMultiDelete(confirm),
                MessageBox,
                f"Delete {selected_count} selected files?\n\nThis cannot be undone!",
                MessageBox.TYPE_YESNO
            )
        else:
            # Originalno ponašanje - brisanje jednog fajla
            selected_idx = self["files"].getSelectedIndex()

            if not self.file_list or selected_idx >= len(self.file_list):
                self["status"].setText("No file selected!")
                return

            file_info = self.file_list[selected_idx]
            filename = file_info['name']
            filepath = file_info['path']

            # Potvrda brisanja
            self.session.openWithCallback(
                lambda confirm: self.confirmDelete(confirm, filepath, filename, selected_idx),
                MessageBox,
                f"Delete file '{filename}'?\n\nSize: {self.format_size(file_info['size'])}\nDate: {file_info['date']}",
                MessageBox.TYPE_YESNO
            )

    def confirmDelete(self, confirmed, filepath, filename, index):
        """Potvrdi brisanje fajla"""
        if not confirmed:
            self["status"].setText("Delete cancelled")
            return

        try:
            import os
            os.remove(filepath)

            # Ukloni iz liste
            if index < len(self.file_list):
                del self.file_list[index]

            # Refresh prikaz
            self.refreshFiles()

            self["status"].setText(f"Deleted: {filename}")
            self.session.open(
                MessageBox,
                f"File '{filename}' deleted successfully!",
                MessageBox.TYPE_INFO,
                timeout=3
            )

        except Exception as e:
            print(f"[FILE EXPLORER] Delete error: {e}")
            self["status"].setText(f"Delete failed: {str(e)[:50]}")
            self.session.open(
                MessageBox,
                f"Error deleting file: {str(e)}",
                MessageBox.TYPE_ERROR
            )

    def renameFile(self):
        """Preimenuj fajl"""
        selected_idx = self["files"].getSelectedIndex()

        if not self.file_list or selected_idx >= len(self.file_list):
            self["status"].setText("No file selected!")
            return

        file_info = self.file_list[selected_idx]
        old_name = file_info['name']

        # Otvori virtualnu tastaturu za novi naziv
        self.session.openWithCallback(
            lambda new_name: self.doRename(new_name, file_info, selected_idx),
            VirtualKeyBoard,
            title=f"Rename file\nCurrent: {old_name}",
            text=os.path.splitext(old_name)[0]
        )

    def doRename(self, new_name, file_info, index):
        """Izvrši preimenovanje"""
        if not new_name:
            return

        import os

        old_path = file_info['path']
        old_dir = os.path.dirname(old_path)
        old_ext = os.path.splitext(file_info['name'])[1]

        # Dodaj ekstenziju ako je korisnik izostavio
        if not new_name.lower().endswith(old_ext.lower()):
            new_name += old_ext

        new_path = os.path.join(old_dir, new_name)

        # Proveri da li novi fajl već postoji
        if os.path.exists(new_path):
            self.session.open(
                MessageBox,
                f"File '{new_name}' already exists!",
                MessageBox.TYPE_ERROR
            )
            return

        try:
            os.rename(old_path, new_path)

            # Ažuriraj listu
            self.refreshFiles()

            self["status"].setText(f"Renamed to: {new_name}")
            self.session.open(
                MessageBox,
                f"File renamed successfully!\n\n{file_info['name']} → {new_name}",
                MessageBox.TYPE_INFO,
                timeout=3
            )

        except Exception as e:
            print(f"[FILE EXPLORER] Rename error: {e}")
            self["status"].setText(f"Rename failed")
            self.session.open(
                MessageBox,
                f"Error renaming file: {str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showFileInfo(self):
        """Prikaži informacije o fajlu"""
        selected_idx = self["files"].getSelectedIndex()

        if not self.file_list or selected_idx >= len(self.file_list):
            self["status"].setText("No file selected!")
            return

        file_info = self.file_list[selected_idx]

        # Pročitaj prvih nekoliko linija fajla
        preview_lines = []
        try:
            with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                for i in range(10):
                    line = f.readline()
                    if not line:
                        break
                    preview_lines.append(line.strip()[:80])
        except:
            preview_lines = ["Could not read file content"]

        # Kreiraj info tekst
        info_text = f"""FILE INFORMATION:

Name: {file_info['name']}
Path: {file_info['path']}
Size: {self.format_size(file_info['size'])}
Date: {file_info['date']}
Type: {self.get_file_type(file_info['name'])}

PREVIEW:
"""
        for i, line in enumerate(preview_lines[:5]):
            info_text += f"{i + 1}. {line}\n"

        if len(preview_lines) > 5:
            info_text += "...\n"

        info_text += "\nPress OK to close"

        self.session.open(
            MessageBox,
            info_text,
            MessageBox.TYPE_INFO
        )

    def format_size(self, size_bytes):
        """Formatiraj veličinu fajla"""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def get_file_type(self, filename):
        """Odredi tip fajla"""
        import os
        ext = os.path.splitext(filename)[1].lower()

        ext_types = {
            '.srt': 'SubRip Subtitle',
            '.sub': 'MicroDVD Subtitle',
            '.ass': 'ASS/SSA Subtitle',
            '.ssa': 'SSA Subtitle',
            '.vtt': 'WebVTT Subtitle',
            '.txt': 'Text File',
            '.zip': 'ZIP Archive'
        }

        return ext_types.get(ext, 'Unknown')

    def refreshFiles(self):
        """Osveži listu fajlova"""
        self["status"].setText("Refreshing...")
        self.loadFiles()

    def up(self):
        if self["files"].getList():
            self["files"].up()

    def down(self):
        if self["files"].getList():
            self["files"].down()

    def left(self):
        if self["files"].getList():
            self["files"].pageUp()

    def right(self):
        if self["files"].getList():
            self["files"].pageDown()

class TitloviBrowser(Screen):
    skin = """
    <screen name="TitloviBrowser" position="center,center" size="1920,1080" title="Titlovi Browser">
        <!-- BACKGROUND -->
        <widget name="background" position="1270,50" size="500,800" pixmap="%s" alphatest="on" zPosition="1" />
    
        <!-- LEVI PANEL -->
        <eLabel position="20,30" size="1150,900" backgroundColor="#333333" zPosition="-1" />
    
        <!-- DESNI PANEL -->
        <eLabel position="1220,30" size="600,900" backgroundColor="#333333" zPosition="-1" />
    
        <!-- CONTENT -->
        <widget name="title" position="50,50" size="1100,60" font="Regular;40" />
        <widget name="info" position="50,120" size="1100,750" font="Regular;28" />
    
        <!-- FOOTER SA BOJENIM TEKSTOM I SIVOM POZADINOM -->
        <eLabel position="20,950" size="1800,100" backgroundColor="#333333" zPosition="-1" />
    
        <eLabel position="50,970" size="300,50" font="Regular;28" foregroundColor="red" halign="center" valign="center" text="EXIT - izlaz" />
        <eLabel position="500,970" size="300,50" font="Regular;28" foregroundColor="green" halign="center" valign="center" text="ZELENO - meni" />
        <eLabel position="950,970" size="300,50" font="Regular;28" foregroundColor="yellow" halign="center" valign="center" text="ŽUTO - pretraga" />
        <eLabel position="1400,970" size="300,50" font="Regular;28" foregroundColor="blue" halign="center" valign="center" text="PLAVO - napredna" />
    </screen>
    """ % BACKGROUND

    def __init__(self, session):
        Screen.__init__(self, session)
        
        self["background"] = Pixmap()

        self["title"] = Label("Titlovi Browser")
        self["info"] = Label("Dobrodošli u Titlovi Browser!\n\n" +
                             "Ova aplikacija vam omogućava:\n" +
                             "• Pretraga Filmova\n" +
                             "• Pregled popularnih filmova\n" +
                             "• Pregled popularnih serija\n" +
                             "• Pretraga filmova\n" +
                             "• Pretraga serija\n" +
                             "• BOX Office Srbija\n" +
                             "• BOX Office Hrvatska\n" +
                             "• BOX Office SAD\n" +
                             "• Konfiguracija\n" +
                             "• Obriši Keš\n" +
                             "• File Explorer\n" +
                             "• ŽUTO dugme: Titlovi Jednostavno (Za Filmove)\n" +
                             "• PLAVO dugme: Titlovi Napredno (Za Serije)\n\n" +
                             "..:: CiefpSettings ::..")
        
        # Ažuriraj action map
        self["actions"] = ActionMap(
            ["DirectionActions", "OkCancelActions", "ColorActions"],
            {
                "cancel": self.exit,
                "back": self.exit,
                "red": self.exit,
                "green": self.openMenu,
                "yellow": self.subtitlesBasic,  # Promenjeno!
                "blue": self.subtitlesAdvanced,  # Promenjeno!
                "ok": self.openMenu,
            },
            -1
        )
        # Inicijalizuj config sekciju
        from Components.config import config, ConfigSubsection, ConfigText

        # Kreiraj config sekciju ako ne postoji
        if not hasattr(config, 'plugins'):
            config.plugins = ConfigSubsection()
        if not hasattr(config.plugins, 'titlovibrowser'):
            config.plugins.titlovibrowser = ConfigSubsection()

        # Učitaj postojecu vrednost ili postavi podrazumevanu
        default_path = config.plugins.titlovibrowser.downloadpath.value if hasattr(config.plugins.titlovibrowser,
                                                                                   'downloadpath') else "/media/hdd/subtitles/"
        self.download_path = ConfigText(default=default_path, fixed_size=False)

        # Sačuvaj u config objekat
        if not hasattr(config.plugins.titlovibrowser, 'downloadpath'):
            config.plugins.titlovibrowser.downloadpath = self.download_path

    def openMenu(self):
        menu = [
            ("Pretraga Filmova", "universal_search"),
            ("Popularni Filmovi", "popular_movies"),
            ("Popularne Serije", "popular_series"),
            ("Novi Filmovi", "new_movies"),
            ("Filmovi", "movies_simple"),
            ("Serije", "series_simple"),
            ("Box Office - Srbija", "boxoffice_srbija"),
            ("Box Office - Hrvatska", "boxoffice_hrvatska"),
            ("Box Office - SAD", "boxoffice_sad"),
            ("Konfiguracija", "config"),  # NOVO
            ("Obriši Keš", "clear_cache"),  # NOVO
            ("File Explorer", "file_explorer"),  # NOVO
        ]
        self.session.openWithCallback(self.menuCallback, ChoiceBox,
                                      title="Titlovi Browser Menu",
                                      list=menu)

    def menuCallback(self, choice):
        if not choice:
            return

        key = choice[1]
        title = choice[0]

        if key == "universal_search":  # NOVO
            self.session.open(UniversalSearchScreen)
        elif key == "popular_movies":
            self._showCategory(parse_popular_movies, "Popularni Filmovi")
        elif key == "popular_series":
            self._showCategory(parse_popular_series, "Popularne Serije")
        elif key == "new_movies":
            self._showCategory(parse_new_movies, "Novi Filmovi")
        elif key == "movies_simple":
            self.session.open(SimpleMoviesScreen)
        elif key == "series_simple":
            self.session.open(SimpleSeriesScreen)
        elif key == "boxoffice_srbija":
            self._showCategory(parse_boxoffice_srbija, "Box Office - Srbija")
        elif key == "boxoffice_hrvatska":
            self._showCategory(parse_boxoffice_hrvatska, "Box Office - Hrvatska")
        elif key == "boxoffice_sad":
            self._showCategory(parse_boxoffice_sad, "Box Office - SAD")
        elif key == "config":  # NOVO
            self.session.open(TitloviConfigScreen)
        elif key == "clear_cache":  # NOVO
            self.clearCacheAction()
        elif key == "file_explorer":
            self.session.open(SubtitleFileExplorer)

    def _showCategory(self, parser_func, title):
        """Pomoćna funkcija za prikaz kategorije"""
        try:
            items = parser_func()
            if items:
                self.session.open(MovieListScreen, title, items)
            else:
                self.session.open(
                    MessageBox,
                    f"Nema podataka za '{title}'.",
                    MessageBox.TYPE_INFO
                )
        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška pri učitavanju '{title}':\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showSeries(self, key, title):
        """Prikazuje popularne serije"""
        try:
            series = parse_popular_series()
            if not series:
                self.session.open(
                    MessageBox,
                    f"Nema podataka za '{title}'.",
                    MessageBox.TYPE_INFO
                )
                return
            self.session.open(MovieListScreen, title, series)
        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška pri preuzimanju '{title}':\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showNewMovies(self, key, title):
        """Prikazuje nove filmove"""
        try:
            movies = parse_new_movies()
            if not movies:
                self.session.open(
                    MessageBox,
                    f"Nema podataka za '{title}'.",
                    MessageBox.TYPE_INFO
                )
                return
            self.session.open(MovieListScreen, title, movies)
        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška pri preuzimanju '{title}':\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showListByCategory(self, category_key, category_title):
        """Prikazuje listu za određenu kategoriju"""
        try:
            if category_key == "popular_movies":
                movies = parse_popular_movies()  # Samo popularni filmovi
            elif category_key == "popular_series":
                movies = parse_popular_series()  # Samo popularne serije
            elif category_key == "new_movies":
                movies = parse_new_movies()  # Samo novi filmovi
            else:
                self.session.open(
                    MessageBox,
                    "Ova sekcija još nije implementirana.",
                    MessageBox.TYPE_INFO
                )
                return

            if not movies:
                self.session.open(
                    MessageBox,
                    f"Nema podataka za '{category_title}'.",
                    MessageBox.TYPE_INFO
                )
                return

            self.session.open(MovieListScreen, category_title, movies)

        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška pri preuzimanju '{category_title}':\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    def showMovies(self, result):
        try:
            movies = parse_popular_movies()

            if not movies:
                self.session.open(
                    MessageBox,
                    "Nema podataka ili greška u parsiranju.",
                    MessageBox.TYPE_ERROR
                )
                return

            self.session.open(MovieListScreen, "Popularni Filmovi", movies)

        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška pri preuzimanju:\n{str(e)}",
                MessageBox.TYPE_ERROR
            )

    # DODAJ OVE DVE NOVE METODE:
    def subtitlesBasic(self):
        """Otvara osnovnu pretragu titlova"""
        self.session.open(SubtitlesBasicScreen)

    def subtitlesAdvanced(self):
        """Otvara naprednu pretragu titlova"""
        self.session.open(SubtitlesAdvancedScreen)

    def searchBasic(self):
        self.session.open(SearchScreen)

    def searchAdvanced(self):
        self.session.open(MessageBox, "Napredna pretraga (u razvoju)", MessageBox.TYPE_INFO)

    def exit(self):
        self.close()

    def clearCacheAction(self):
        """Akcija za brisanje cache-a"""
        from enigma import eTimer

        self.session.openWithCallback(
            self.confirmClearCache,
            MessageBox,
            "Da li želite da obrišete SAV cache?\n\n" +
            f"{get_cache_size()}\n\n" +
            "Ovo će obrisati sve keširane postere,\nHTML stranice i titlove.",
            MessageBox.TYPE_YESNO
        )

    def confirmClearCache(self, result):
        if result:
            success, message = clear_cache()

            mtype = MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR
            self.session.open(
                MessageBox,
                message,
                mtype,
                timeout=5
            )


def main(session, **kwargs):
    session.open(TitloviBrowser)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=f"{PLUGIN_NAME} v{PLUGIN_VERSION}",
            description="Pregled Titlovi.com sadržaja",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=os.path.join(PLUGIN_PATH, "icon.png"),
            fnc=main
        ),
        PluginDescriptor(
            name="Titlovi Browser",
            description="Pregled Titlovi.com sadržaja",
            where=PluginDescriptor.WHERE_EXTENSIONSMENU,
            fnc=main
        )
    ]