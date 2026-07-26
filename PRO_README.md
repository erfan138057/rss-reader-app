# 🎙️ RSS Reader Pro - Professional RSS Management Desktop App

A comprehensive Python desktop application for managing RSS feeds with advanced privacy and video features.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%2C%20Linux%2C%20Mac-lightgrey)

## ✨ Key Features

- ⚡ **DNS-over-HTTPS Support** - Bypass internet filters with secure connections
- 🎬 **Redgifs Video Playback** - Native support for Redgifs videos
- 🎧 **Audio Control** - Volume controls in VLC player (+/- buttons)
- 🌟 **Dual UI Themes** - Reddit-style and Telegram-style interfaces
- ⚡ **Smart Caching** - Fast performance with intelligent caching
- 🛡️ **Privacy First** - No data sent to external servers, local SQLite storage
- 📺 **YouTube Support** - Direct YouTube video detection and playback
- 🔍 **Content Detection** - Automatic detection of videos and images in feeds

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- VLC Media Player (for video playback)

### Installation
\`\`\`bash
# Clone the repository
git clone https://github.com/erfan138057/rss-reader-app.git
cd rss-reader-app

# Install dependencies
pip install -r requirements.txt

# Run the application
python gui.py
\`\`\`

### Windows EXE (Coming Soon)
Standalone executable will be available in Releases section.

## 🎯 Use Cases

- **Iranian Users**: Bypass internet filters with DNS-over-HTTPS
- **Privacy Enthusiasts**: Complete local operation, no external servers
- **Video Consumers**: Redgifs and YouTube video support
- **Python Developers**: Clean, modular code for learning and contribution
- **RSS Power Users**: Advanced feed management with modern features

## 📖 Documentation

### Basic Usage
1. Add RSS feeds through the interface
2. Browse articles in Reddit or Telegram style
3. Click on videos to play them in built-in VLC player
4. Use DNS-over-HTTPS for secure connections in restricted networks

### Video Playback
- Redgifs videos play natively in VLC
- YouTube videos open in browser or can be played externally
- Volume controls available during playback

### Privacy Features
- All data stored locally in SQLite
- DNS-over-HTTPS encrypts DNS queries
- No telemetry or external data collection

## 🛠️ Technical Details

### Built With
- **Python 3.8+** - Core programming language
- **Tkinter** - GUI framework
- **VLC** - Video playback via python-vlc
- **SQLite** - Local data storage
- **Requests** - HTTP client with DoH support

### Architecture
- Modular design (core, gui, config separated)
- Threading for non-blocking UI
- Smart caching system for performance
- Comprehensive error handling

## 🤝 Contributing

We love contributions! Here's how you can help:

1. **Report Bugs**: Open an issue with detailed description
2. **Suggest Features**: Share your ideas in Discussions
3. **Submit Code**: Send pull requests for improvements
4. **Improve Docs**: Help us make documentation better

### Development Setup
\`\`\`bash
# Fork and clone the repository
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate  # Windows

# Install development dependencies
pip install -r requirements.txt

# Run tests
python test_core.py
\`\`\`

## ❓ Frequently Asked Questions

**Q: Why DNS-over-HTTPS?**
A: To bypass internet filters and provide secure DNS resolution in restricted networks.

**Q: Does it work in Iran?**
A: Yes! The DNS-over-HTTPS feature helps bypass filters, and all operations are local.

**Q: Are my feeds private?**
A: Absolutely. All data is stored locally on your machine, no external servers involved.

**Q: Can I add my own video platforms?**
A: Yes! The video detection system is modular and easily extendable.

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/erfan138057/rss-reader-app?style=social)
![Git forks](https://img.shields.io/github/forks/erfan138057/rss-reader-app?style=social)
![GitHub issues](https://img.shields.io/github/issues/erfan138057/rss-reader-app)

## 👥 Community

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Ideas and questions
- **Twitter**: Follow for updates

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- VLC team for excellent media playback
- Python community for amazing tools and libraries
- Open-source contributors who make projects like this possible

---

⭐ **If you find this project useful, please give it a star on GitHub!** ⭐