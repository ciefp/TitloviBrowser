![Enigma2 Plugin](https://img.shields.io/badge/Enigma2-Plugin-blue.svg)
![Version](https://img.shields.io/badge/Version-1.0-green.svg)
![License](https://img.shields.io/badge/License-GPL-yellow.svg)

# Titlovi Browser v1.0

Titlovi Browser is a comprehensive Enigma2 plugin for browsing movies, TV series, and subtitles from Titlovi.com - the largest subtitle portal for Balkan languages.

## 📸 Screenshots
![TitloviBrowser](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-1.jpg)
![TitloviBrowser](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-4.jpg)
![TitloviBrowser](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-6.jpg)
![TitloviBrowser](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-8.jpg)
![TitloviBrowser](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-9.jpg)

| Menu | Search simple |
|-------------|----------|
| ![Menu](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-2.jpg) | ![search simple](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-3.jpg) |

| Search result  | Movies  |
|----------------|-----------------|
| ![Menu](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-5.jpg) | ![search simple](https://github.com/ciefp/TitloviBrowser/blob/main/titlovibrowser-7.jpg) |
## ✨ Features

### 🎥 Movies & TV Shows
- Browse popular movies
- Browse popular TV series
- New movies in cinemas
- Detailed movie information (poster, plot, ratings, cast, director)

### 🎯 BOX Office lists:
- Serbia
- Croatia
- USA

### 🔍 Search Functionality
- Universal search for movies and TV series
- Search by multiple criteria:
  - Title
  - Year range (from-to)
  - Genre
  - IMDB ID
- Different sorting options

### 📝 Subtitles
- Basic subtitle search for movies
- Advanced subtitle search for TV series (with seasons/episodes)
- File Explorer for managing downloaded subtitles
- Automatic subtitle download to configured folder

### ⚙️ Configuration
- Customizable download path (`/media/hdd/subtitles/` by default)
- Default subtitle language (Serbian, Croatian, Bosnian, etc.)
- Cache memory limit
- Debug options
- Cache clearing functionality

## 🚀 Installation

### Manual Installation
Copy wget link to telnet

## 📖 Usage

### Main Menu Options:
- **Movie Search** - Universal search for movies/series
- **Popular Movies** - Browse trending movies
- **Popular Series** - Browse trending TV series
- **New Movies** - Latest cinema releases
- **Movies** - Simple movie browser
- **Series** - Simple series browser
- **BOX Office Lists** - View box office rankings
- **Configuration** - Plugin settings
- **Clear Cache** - Clear temporary files
- **File Explorer** - Browse downloaded subtitles

### Keyboard Shortcuts:
- **EXIT** - Back/Close
- **GREEN** - Open menu/Select
- **YELLOW** - Basic subtitle search
- **BLUE** - Advanced subtitle search
- **OK** - Open virtual keyboard/Select

## 🔧 Technical Details

### System Requirements
- Enigma2-based receiver (Vu+, Dreambox, Octagon, etc.)
- Python 3
- Internet connection
- Minimum 50MB free space

### File Structure
```bash
TitloviBrowser/
├── plugin.py # Main plugin file
├── parser.py # Web scraping module
├── titlovi_api.py # API integration
├── icon.png # Plugin icon
├── background.png # Background image
└── README.md # This file
```

### Cache Management
The plugin caches:
- Movie/TV show posters
- HTML pages for faster loading
- Search results

**Cache location:** `/tmp/Titlovi_Browser/`
- Auto-clearing available in settings
- Configurable size limits

## ⚠️ Limitations (v1.0)

### Current Limitations:
- Maximum 60 results per list (for stability)
- No auto-download based on playing video
- No integration with Enigma2 video player
- No favorites system yet

### Known Issues:
- Some posters may not load due to size restrictions
- Search might be slow on low-end receivers
- Memory usage increases with cache size

## 🔮 Planned Features

### Short-term:
- Auto-detection of currently playing video
- Auto-download matching subtitles
- Favorites/Bookmarks system
- More languages for interface

### Long-term:
- IMDB integration
- Trailer playback
- User accounts
- Multi-language interface
- Skin customization

## 🤝 Contributing
Contributions are welcome! Here's how you can help:

- **Report Bugs:** Open an issue with detailed information
- **Suggest Features:** Share your ideas for improvements
- **Code Contributions:** Fork and submit pull requests
- **Translation:** Help translate the interface
- **Testing:** Test on different Enigma2 receivers

### Development Setup:
```bash
# Clone repository
git clone https://github.com/yourusername/TitloviBrowser.git

# Install on your receiver via FTP
# Test and debug using Enigma2 logs
```

## 📄 License
This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## ❤️ Acknowledgments
- Titlovi.com for providing the content
- Enigma2 community for support and testing
- Open source contributors
- All beta testers

## 📞 Support
Need Help?
- Documentation: Check this README first
- Issues: Use GitHub Issues for bug reports
- Discussions: GitHub Discussions for questions

## Compatibility:
Tested on:
- Vu+ Zero 4K
- Dreambox DM920
- Octagon SF8008
- Zgemma H9.2H

Should work on all Enigma2 receivers with Python3 support.

## 📊 Statistics
- Plugin Size: ~500KB
- Memory Usage: ~20-50MB
- Cache Size: Configurable (default 20MB)
- Supported Languages: 7 subtitle languages

Note: This is the first stable release. Please report any issues you encounter for quicker fixes in future updates.

# Enjoy your movies with perfect subtitles! 🎬✨

