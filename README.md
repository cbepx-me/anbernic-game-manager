# Anbernic Game Manager

🎮 A self‑hosted game management suite for Anbernic handheld consoles (RG35XX+, RG40XX, RG CubeXX, etc.)  
Provides both a **web interface** (accessible from any browser) and a **native on‑device UI** for managing ROMs, previews, guides, and save data – all without removing the SD card.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.2-lightgrey)](https://flask.palletsprojects.com)

---

## ✨ Features

- **Browse ROMs** – organised by console, supports both SD1 and SD2 storage.
- **Upload / Delete** – add games, preview images (PNG/JPG), and guide text files.
- **Automatic Scraping** – fetch screenshots from [ScreenScraper.fr](https://www.screenscraper.fr) (requires free account).
- **Batch Operations** – scrape missing previews, rename files in bulk (prefix/suffix, remove brackets, etc.).
- **Metadata Import** – import games and previews from `gamelist.xml` or `metadata.pegasus.txt`.
- **Save Backup / Restore** – backup all emulator save states and memory cards to a `.tar.gz` archive.
- **Preview & Guide** – display cover art and read guide files alongside the game details.
- **Web Interface** – fully responsive, works on mobile, tablet, and desktop.
- **Native UI** – SDL2‑based on‑device interface with gamepad controls.
- **Multi‑language** – supports English, Chinese, Japanese, Korean, and more.
- **Safe Shutdown** – stop the server gracefully from the web UI.

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
<div align="center">
<img width="640" height="480" alt="screenshot_20260822_181245" src="https://github.com/user-attachments/assets/cc786c9b-8432-4565-b339-eeb7eb9a6a0e" />

<img width="640" height="480" alt="screenshot_20260822_181254" src="https://github.com/user-attachments/assets/6e9cc2cd-6c75-40a4-a096-c9b2f7b3e44d" />
---

### Web UI

<img width="1860" height="1227" alt="屏幕截图 2026-08-22 175448" src="https://github.com/user-attachments/assets/7c08aee6-0639-42ca-a09e-995146e0edc8" />

Main dashboard – browse games, view previews, and manage files.

<img width="400" height="1069" alt="bcde2f0066806f17b35c458bd99e8825" src="https://github.com/user-attachments/assets/053ea64b-397a-4471-98e9-3506e1d3a869" />

Mobile main interface – browse games, view details, and manage files on the go.

---

### Local UI

<img width="640" height="480" alt="screenshot_20260822_181332" src="https://github.com/user-attachments/assets/01c4be41-a61b-4cda-8ba7-504005e08509" />

Main dashboard – browse games, view previews, and manage files.

<img width="640" height="480" alt="screenshot_20260822_181339" src="https://github.com/user-attachments/assets/846d23b4-4a94-44d6-b71e-a57ee1902ec9" />

Game details interface.

<img width="640" height="480" alt="screenshot_20260822_181352" src="https://github.com/user-attachments/assets/2aa408e3-2842-43a4-8481-bbfd14710fde" />

<img width="640" height="480" alt="screenshot_20260822_181345" src="https://github.com/user-attachments/assets/56cfd9b0-498d-4f73-a0a6-3dca025c241e" />

Function Menu.

</div>
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
