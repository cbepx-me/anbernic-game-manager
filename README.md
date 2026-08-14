# Anbernic Game Manager

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.2-lightgrey)](https://flask.palletsprojects.com)

A lightweight, web-based management tool for Anbernic handheld gaming consoles.  
Easily manage your ROMs, scrape box art, backup/restore save data, upload game guides, and more – all from your browser.

> **Designed for Anbernic devices** (RG35XX, RG40XX, RG CubeXX, etc.) running the stock firmware with Python 3.8+.

---

## ✨ Features

- **📁 ROM Management** – Browse, upload, and delete games (supports many systems: GBA, PS1, PSP, MAME, etc.)
- **🖼️ Cover Art Scraping** – Fetch screenshots individually or in batch from ScreenScraper (supports multi‑language game names)
- **✏️ Rename Games** – Rename ROM files and their associated preview images
- **📄 Game Guides** – Upload `.txt` guide files for any game
- **💾 Save Data Backup & Restore** – One‑click backup of all save data (PPSSPP, PCSX, RetroArch, Drastic, etc.) as a `.tar.gz` archive, with verification on restore
- **🔁 Dual SD Card Support** – Switch between SD1 and SD2, view storage usage in real time
- **🌍 Multi‑language** – UI supports Chinese, English, Japanese, Korean, and more (system language auto‑detected)
- **📱 Mobile Friendly** – Responsive design works on phones and tablets

---

## 📋 Requirements

- Anbernic device with stock firmware (or compatible Linux environment)
- Python 3.8+ (pre‑installed on most Anbernic devices)
- Network connection (Wi‑Fi) for web access and scraping
- ScreenScraper account (optional, required for scraping) – [sign up here](https://www.screenscraper.fr)

---

## 🚀 Installation

1. **Clone the repository** onto your Anbernic device (via SSH or SCP):
   ```bash
   git clone https://github.com/yourusername/anbernic-game-manager.git
   cd anbernic-game-manager
   ```
2. **Install dependencies** (if not already present):
   ```bash
    python3 -m pip install -r requirements.txt
   ```
> Note: The script will attempt to auto‑install missing modules on first run.

3. **Configure ScreenScraper** (optional but recommended):
    Copy `config.json` and fill in your ScreenScraper credentials:
    ```json
    {
      "user": "your_username",
      "password": "your_password",
      "media_type": "ss",
      "region": "wor"
    }
    ```
4. **Run the manager**:
    ```bash
    python3 main.py
    ```

    The splash screen will appear on the device, and a web server starts on port `5000`.

5. **Access the web UI**:
    Open a browser on your computer/phone and navigate to:
    ```text
    http://<device-ip>:5000
    ```

    (You can find the IP address on the splash screen.)

> 💡 To stop the server, press the SELECT button on the device or visit `/shutdown` in the browser.

## 🎮 Supported Systems

The manager recognizes ROMs by file extension. A full list is in `systems.py`.
Examples: GBA, NES, SNES, N64, PS1, PSP, MAME, FBNeo, Dreamcast, and many more.

## 🛠️ Configuration

- `config.json` – ScreenScraper credentials and scraping options.

- `lang/` – Translation files (JSON) – add or modify languages.

- `csv/` – Arcade game name mapping (arcade-plus.csv) – edit to customize display names.

## 📂 Backup & Restore

- Backup: Creates a `.tar.gz` archive of all save data directories (PPSSPP, PCSX, RetroArch, Drastic, etc.). The file is downloaded to your computer.

- Restore: Upload a previously downloaded backup file; the system verifies it contains a valid marker before extracting.

## 🖼️ Screenshots

(Add screenshots here to showcase the interface)

https://screenshots/dashboard.png

Main dashboard – browse games, view previews, and manage files.

https://screenshots/scraping.png

Batch scraping cover art for all games in a directory.

https://screenshots/backup.png

Backup and restore save data with one click.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](https://github.com/cbepx-me/anbernic-game-manager/blob/main/CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](https://github.com/cbepx-me/anbernic-game-manager/blob/main/LICENSE) file for details.

## 🙏 Acknowledgements

- ScreenScraper for the amazing scraping API.

- The Anbernic community for testing and feedback.

Author: G.R.H
Project Page: GitHub
