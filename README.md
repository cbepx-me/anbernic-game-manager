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

## 🖥️ Supported Devices & OS

This tool is specifically designed for **all open‑source handheld devices powered by the H700 CPU**, commonly found in recent Anbernic models. It has been tested and verified on:

- **Supported devices I** (H700‑based): RG35XX Plus, RG35XX H, RG35XX SP, RG40XX H, RG40XX V, RG CubeXX, and other H700‑based handhelds.
- **Supported devices II** (RK3568‑based): RGdsX, and other RK3568‑based handhelds.
- **Supported operating systems**: Stock OS (the official firmware) and [Stock OS MOD](https://github.com/cbepx-me/Anbernic-H700-RG-xx-StockOS-Modification) (community‑modified versions based on the original firmware).

> **Note**: While it may work on other Linux‑based handhelds with similar directory structures, full compatibility is only guaranteed on H700 devices running Stock OS or Stock OS MOD.

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

---

## 🎮 Supported Systems

The manager recognizes ROMs by file extension. A full list is in `systems.py`.
Examples: GBA, NES, SNES, N64, PS1, PSP, MAME, FBNeo, Dreamcast, and many more.

---

## 🛠️ Configuration

- `config.json` – ScreenScraper credentials and scraping options.

- `lang/` – Translation files (JSON) – add or modify languages.

- `csv/` – Arcade game name mapping (arcade-plus.csv) – edit to customize display names.

---

## 📂 Backup & Restore

- Backup: Creates a `.tar.gz` archive of all save data directories (PPSSPP, PCSX, RetroArch, Drastic, etc.). The file is downloaded to your computer.

- Restore: Upload a previously downloaded backup file; the system verifies it contains a valid marker before extracting.

---

## 🖼️ Screenshots

<img width="720" height="480" alt="screenshot_20260820_091019" src="https://github.com/user-attachments/assets/ab37ee38-e52b-45a2-a2ec-e1a00ee1cf34" />

<img width="720" height="480" alt="screenshot_20260819_233257" src="https://github.com/user-attachments/assets/00bc5807-3a28-4b7d-b867-e0ba07aa5427" />


### Web UI

<img width="1860" height="1225" alt="屏幕截图 2026-08-19 233459" src="https://github.com/user-attachments/assets/308ee0d5-4f1b-4236-bab9-e5a1d0679848" />

Main dashboard – browse games, view previews, and manage files.

<div align="center">
<img width="400" height="882" alt="1f67a19399b17dadb4ffd65c63995807" src="https://github.com/user-attachments/assets/4d09b7b1-162a-4098-bb2e-8f2abb118ea7" />
</div>

Mobile main interface – browse games, view details, and manage files on the go.

### Local UI

<img width="720" height="480" alt="screenshot_20260819_233349" src="https://github.com/user-attachments/assets/461ea82d-ecef-4ffd-b661-0de11f0917ac" />

Main dashboard – browse games, view previews, and manage files.

<img width="720" height="480" alt="screenshot_20260819_233358" src="https://github.com/user-attachments/assets/7b82ac94-9cf0-4e8d-a23f-2395117762da" />

Game details interface.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](https://github.com/cbepx-me/anbernic-game-manager/blob/main/CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](https://github.com/cbepx-me/anbernic-game-manager/blob/main/LICENSE) file for details.

---

## 🙏 Acknowledgements

- ScreenScraper for the amazing scraping API.

- The Anbernic community for testing and feedback.

---

Author: G.R.H (cbepx-me)
Project Page: [GitHub](https://github.com/cbepx-me/anbernic-game-manager)
