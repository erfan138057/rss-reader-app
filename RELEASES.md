# RSS Reader - Release Notes

## 📦 Version 1.0.0 - Initial Release
**Release Date:** January 2025  
**Status:** Stable  
**Download:** [rss-reader-v1.0.0.exe](https://github.com/yourusername/rss-reader/releases/tag/v1.0.0)

### ✨ New Features
- **DNS-over-HTTPS (DoH) Support**: Bypass censorship with built-in DNS scanner
- **Video Playback**: Full support for YouTube, Vimeo, Redgifs, and direct video links
- **Dual UI Styles**: Telegram-style chat view and Reddit-style card view
- **Multi-language**: English and Persian (Farsi) support
- **Smart Caching**: Reduce bandwidth usage with intelligent feed caching
- **Internet Monitoring**: Real-time network status monitoring

### 🎯 Key Features
- **DNS Scanner**: Test and select fastest DNS servers
- **Video Detection**: Auto-detect video platforms from links
- **Image Support**: Display images from feeds
- **Customizable**: Multiple themes, font sizes, and display options
- **Persistent Settings**: Save preferences between sessions

### 🛠️ Technical Details
- **Platform**: Windows (Tkinter-based)
- **Dependencies**: httpx, feedparser, Pillow, python-vlc
- **Database**: SQLite for feed storage
- **Cache**: In-memory caching with expiration

### 🐛 Bug Fixes
- Fixed DNS resolution issues
- Improved video playback reliability
- Enhanced error handling
- Better memory management

---

## 📦 Version 0.9.0 - Beta Release
**Release Date:** December 2024  
**Status:** Beta  

### 🔧 Initial Implementation
- Basic RSS feed parsing and display
- DNS-over-HTTPS foundation
- Video detection framework
- Persian language support
- Basic caching system

### 📋 Tested Features
- ✅ YouTube video detection and playback
- ✅ Redgifs support
- ✅ DNS server scanning
- ✅ Persian/English language switching
- ✅ Telegram/Reddit view styles
- ✅ Image display from feeds

---

## 🚀 Future Roadmap

### Version 1.1.0 (Q1 2025)
- [ ] Advanced caching with Redis support
- [ ] More video platform integrations
- [ ] Export/import feed lists
- [ ] Keyboard shortcuts
- [ ] System tray integration

### Version 1.2.0 (Q2 2025)
- [ ] Mobile companion app
- [ ] Cloud sync between devices
- [ ] Advanced filtering rules
- [ ] Plugin system for extensions

### Version 2.0.0 (Q3 2025)
- [ ] Cross-platform support (Linux, macOS)
- [ ] Web dashboard
- [ ] API for developers
- [ ] Advanced analytics

---

## 📊 System Requirements

### Minimum
- **OS**: Windows 10 or later
- **RAM**: 2GB
- **Storage**: 50MB free space
- **Internet**: Broadband connection

### Recommended
- **OS**: Windows 11
- **RAM**: 4GB+  
- **Storage**: 100MB free space
- **VLC**: Installed for best video experience

---

## 🔧 Installation

### Windows Executable
1. Download the `.exe` file from Releases
2. Double-click to run (no installation required)
3. Add your RSS feeds in the application

### From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/rss-reader.git
cd rss-reader

# Install dependencies
pip install -r requirements.txt

# Run the application
python gui.py
```

---

## 📝 Changelog

### v1.0.0
- Initial stable release
- Complete Persian translation
- All core features implemented
- Comprehensive test suite
- Windows executable build

### v0.9.0
- Beta release with core functionality
- Basic testing framework
- Initial Persian support
- DNS scanner implementation

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/rss-reader/issues)
- **Documentation**: [README.md](README.md)
- **Email**: your-email@example.com

---

*Last Updated: January 2025*