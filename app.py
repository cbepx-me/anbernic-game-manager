#!/usr/bin/env python3

import os
import sys
from pathlib import Path

base_path = os.path.dirname(os.path.abspath(__file__))
deps_path = os.path.join(base_path, "deps")
if os.path.isdir(deps_path):
    sys.path.insert(0, deps_path)
else:
    sys.exit("Dependencies not found. Please ensure the 'deps' directory exists.")

import glob
import socket
import threading
import subprocess
import tempfile
import shutil
import time
from flask import Flask, request, jsonify, send_file, render_template_string
import pypinyin
from pypinyin import Style
import xml.etree.ElementTree as ET
import shutil

from scraper import Scraper, Rom
from systems import systems, get_system_id
from anbernic import Anbernic
from language import Translator
from name_converter import name_converter
import input

ver = "1.2.1"

board_info = "Unknown"
system_version = "Unknown"

try:
    board_info = Path("/mnt/vendor/oem/board.ini").read_text().splitlines()[0]
    board_mapping = {
        'RGcubexx': 1,
        'RG34xx': 2,
        'RG34xxSP': 2,
        'RGSP': 2,
        'RG28xx': 3,
        'RG35xx+_P': 4,
        'RG35xxH': 5,
        'RG35xxSP': 6,
        'RG40xxH': 7,
        'RG40xxV': 8,
        'RG35xxPRO': 9,
        "RGds": 10,
        "RGdsplus": 11
    }
    hw_info = board_mapping.get(board_info, 5)
except:
    hw_info = 5

try:
    import sdl2
    from PIL import Image
    SDL_AVAILABLE = True
except ImportError:
    SDL_AVAILABLE = False

from graphic import screen_resolutions, UserInterface

scraper = Scraper()
gr = UserInterface()
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_path):
    scraper.load_config_from_json(config_path)
else:
    print("Warning: config.json not found, scraper may not work.")

try:
    lang_info = Path("/mnt/vendor/oem/language.ini").read_text().splitlines()[0]
    system_list = ['zh_CN', 'zh_TW', 'en_US', 'ja_JP', 'ko_KR', 'es_LA', 'ru_RU', 'de_DE', 'fr_FR', 'pt_BR']
    system_lang = system_list[int(lang_info)]
except (FileNotFoundError, IndexError):
    system_lang = 'en_US'

EXT_TO_SYSTEM = {}
for system in systems:
    for ext in system["extensions"]:
        EXT_TO_SYSTEM[ext] = system["name"]

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
app.config['MAX_FORM_PARTS'] = 10000

ALLOWED_IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
PREVIEW_DIR_NAME = "Imgs"

device = Anbernic()
translator = Translator(system_lang)
ARCADE_SYSTEMS = {
    "ATOMISWAVE", "CPS1", "CPS2", "CPS3", "FBNEO",
    "HBMAME", "MAME", "NAOMI", "NEOGEO", "OEM_GAME", "PGM2", "VARCADE"
}
RENAME_BLACKLIST = ARCADE_SYSTEMS | {"DOS", "EASYRPG", "ONS", "SCUMMVM"}
current_sd = device.get_sd_storage()

BACKUP_FILE = "/mnt/mmc/anbernic/backup/save.tar.gz"
BACKUP_MARKER_FILE = "/tmp/anbernic_backup_marker"
BACKUP_DIR = os.path.dirname(BACKUP_FILE)
BACKUP_PATHS = [
    "/mnt/mmc/.config/ppsspp/PSP/PPSSPP_STATE/",
    "/mnt/mmc/.config/ppsspp/PSP/SAVEDATA/",
    "/mnt/mmc/.pcsx/memcards/",
    "/mnt/mmc/.pcsx/sstates/",
    "/mnt/mmc/.pixel_reader_store/",
    "/mnt/mmc/openbor/Saves/",
    "/mnt/mmc/save/",
    "/mnt/mmc/save_nds/",
    "/mnt/mmc/saves_RA/",
    "/mnt/mmc/states_RA/",
    "/mnt/sdcard/.config/ppsspp/PSP/PPSSPP_STATE/",
    "/mnt/sdcard/.config/ppsspp/PSP/SAVEDATA/",
    "/mnt/sdcard/.pcsx/memcards/",
    "/mnt/sdcard/.pcsx/sstates/",
    "/mnt/sdcard/.pixel_reader_store/",
    "/mnt/sdcard/openbor/Saves/",
    "/mnt/sdcard/save/",
    "/mnt/sdcard/save_nds/",
    "/mnt/sdcard/saves_RA/",
    "/mnt/sdcard/states_RA/",
    "/mnt/vendor/deep/drastic-modify/res/backup/",
    "/mnt/vendor/deep/drastic-modify/res/savestates/",
    "/mnt/vendor/deep/retro/system/dc/vmu_save_A1.bin",
    "/mnt/vendor/deep/retro/system/dc/vmu_save_B1.bin",
    "/mnt/vendor/deep/retro/system/dc/vmu_save_C1.bin",
    "/mnt/vendor/deep/retro/system/dc/vmu_save_D1.bin"
]


def is_connected() -> bool:
    test_servers = [
        ("8.8.8.8", 53),
        ("1.1.1.1", 53),
        ("223.5.5.5", 53),
        ("220.181.38.148", 80),
        ("114.114.114.114", 53),
    ]
    try:
        socket.gethostbyname("github.com")
        return True
    except socket.gaierror:
        print("DNS resolution failed")
    for host, port in test_servers:
        try:
            socket.setdefaulttimeout(3)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            print("Network connection test passed with %s:%s", host, port)
            return True
        except (socket.timeout, socket.error) as e:
            print("Connection test failed for %s:%s: %s", host, port, e)
            continue
    print("All network connection tests failed")
    return False

def show_splash_screen(ip):
    print("[DEBUG] show_splash_screen called")
    try:
        from graphic import UserInterface
        ui = UserInterface()
        print("[DEBUG] UI instance created")
        ui.draw_clear()

        box_width = 620
        box_height = 430
        box_x = (ui.screen_width - box_width) // 2
        box_y = (ui.screen_height - box_height) // 2

        ui.draw_rectangle_r(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            radius=15,
            fill="#1a1a2e",
            outline="#0072bb"
        )

        title = f'★ {translator.translate("Anbernic game management")} ★'
        ui.draw_text((ui.screen_width // 2, box_y + 50), title, font=32, color="#ffffff", anchor="mm")

        url_text = f"http://{ip}:5000"
        ui.draw_text((ui.screen_width // 2, box_y + 100), url_text, font=32, color="#00d7ff", anchor="mm")

        qr_success = False
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,
                border=2,
            )
            qr.add_data(f"http://{ip}:5000")
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
            qr_img.thumbnail((160, 160))

            paste_x = (ui.screen_width - qr_img.width) // 2
            paste_y = box_y + 140
            ui.active_image.paste(qr_img, (paste_x, paste_y), qr_img)
            qr_success = True
        except ImportError:
            print((ui.screen_width // 2, box_y + 190), "QR code library not installed")

        if qr_success:
            qr_text = translator.translate("Scan QR code or visit the URL above")
            ui.draw_text((ui.screen_width // 2, box_y + 320), qr_text, font=25, color="#ffd700", anchor="mm")
        else:
            open_text = translator.translate("Open this address in your browser")
            ui.draw_text((ui.screen_width // 2, box_y + 230), open_text, font=25, color="#ffd700", anchor="mm")

        hint = translator.translate("Press SELECT to exit")
        ui.draw_text((ui.screen_width // 2, box_y + box_height - 35), hint, font=23, color="#888888", anchor="mm")
        ui.draw_text((box_x + box_width - 50, box_y + box_height - 35), f"v{ver}", font=23, color="#888888", anchor="mm")

        ui.draw_paint()
        print("[DEBUG] splash screen finished")
    except Exception as e:
        print(f"屏幕显示异常: {e}")
        import traceback
        traceback.print_exc()

def show_error_screen():
    try:
        from graphic import UserInterface
        ui = UserInterface()
        ui.draw_clear()
        box_width = 600
        box_height = 260
        box_x = (ui.screen_width - box_width) // 2
        box_y = (ui.screen_height - box_height) // 2 - 20
        ui.draw_rectangle_r(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            radius=15,
            fill="#1a1a2e",
            outline="#0072bb"
        )
        title = f'✘ {translator.translate("No Internet Connection")} ✘'
        ui.draw_text((ui.screen_width // 2, box_y + 45), title, font=32, color="#cb0202", anchor="mm")
        open_text = translator.translate("Please check your network settings")
        ui.draw_text((ui.screen_width // 2, box_y + 135), open_text, font=29, color="#ffd700", anchor="mm")
        ui.draw_paint()
    except Exception as e:
        print(f"屏幕显示异常: {e}")
        import traceback
        traceback.print_exc()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return str(ip)
    except:
        return '127.0.0.1'

def safe_filename(filename):
    filename = filename.replace('/', '_').replace('\\', '_')
    while '..' in filename:
        filename = filename.replace('..', '_')
    filename = ''.join(c for c in filename if ord(c) >= 32)
    filename = filename.strip()
    if not filename:
        filename = 'unnamed'
    return filename

def get_rom_root(sd=None):
    global current_sd

    if sd is not None:
        current_sd = sd
    
    if current_sd == 1:
        path = device.get_sd1_storage_path()
    else:
        path = device.get_sd2_storage_path()
    print(f"[DEBUG] get_rom_root -> {path}, exists: {os.path.exists(path)}")
    return path

def get_preview_path(game_full_path):
    game_dir = os.path.dirname(game_full_path)
    game_basename = os.path.basename(game_full_path)
    name_without_ext = os.path.splitext(game_basename)[0]
    preview_dir = os.path.join(game_dir, PREVIEW_DIR_NAME)
    if not os.path.isdir(preview_dir):
        return None
    for ext in ALLOWED_IMAGE_EXT:
        candidate = os.path.join(preview_dir, name_without_ext + ext)
        if os.path.exists(candidate):
            return candidate
    return None

def get_guide_path(game_full_path):
    guide_dir = os.path.dirname(game_full_path)
    game_basename = os.path.basename(game_full_path)
    name_without_ext = os.path.splitext(game_basename)[0]
    if not os.path.isdir(guide_dir):
        return None
    candidate = os.path.join(guide_dir, name_without_ext + '.txt')
    if os.path.exists(candidate):
        return candidate
    return None

def detect_system_from_ext(filename):
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return EXT_TO_SYSTEM.get(ext, "Unknown")

def get_subdirs(sd=None):
    rom_root = get_rom_root(sd=sd)
    if not os.path.isdir(rom_root):
        print(f"[DEBUG] ROM root {rom_root} is not a directory")
        return []
    dirs = []
    for item in os.listdir(rom_root):
        if item in ["APPS", "PORTS", "EASYRPG", "ONS"]:
            continue
        full = os.path.join(rom_root, item)
        if os.path.isdir(full) and not item.startswith('.') and item != PREVIEW_DIR_NAME:
            game_count, preview_count = count_games_in_directory(full, check_preview=False, recursive=True)
            dirs.append({
                'name': item,
                'path': item,
                'is_dir': True,
                'has_games': game_count > 0,
                'game_count': game_count,
                'preview_count': preview_count
            })
    dirs.sort(key=lambda x: x['name'].lower())
    print(f"[DEBUG] get_subdirs found {len(dirs)} directories")
    return dirs

def count_games_in_directory(dir_path, check_preview=True, recursive=True):
    game_count = 0
    preview_count = 0
    if recursive:
        for root, _, files in os.walk(dir_path):
            if PREVIEW_DIR_NAME in root.split(os.sep):
                continue
            for f in files:
                if f.startswith('.'):
                    continue
                if detect_system_from_ext(f) != "Unknown" or f.endswith('.zip'):
                    game_count += 1
                    game_path = os.path.join(root, f)
                    if check_preview:
                        if get_preview_path(game_path) is not None:
                            preview_count += 1
    else:
        try:
            for f in os.listdir(dir_path):
                full_path = os.path.join(dir_path, f)
                if os.path.isfile(full_path) and not f.startswith('.'):
                    if detect_system_from_ext(f) != "Unknown" or f.endswith('.zip'):
                        game_count += 1
                        if check_preview:
                            if get_preview_path(full_path) is not None:
                                preview_count += 1
        except OSError:
            pass
    return game_count, preview_count

def get_files_in_dir(subdir, lang=None):
    if subdir in ["APPS", "PORTS", "EASYRPG", "ONS"] or subdir.startswith("APPS/") or subdir.startswith("PORTS/") or subdir.startswith("EASYRPG/") or subdir.startswith("ONS/"):
        return []
    rom_root = get_rom_root()
    target_dir = os.path.join(rom_root, subdir)
    if not os.path.isdir(target_dir):
        return []
    top_dir = subdir.split('/')[0] if subdir else ''
    items = []
    for item in os.listdir(target_dir):
        full_path = os.path.join(target_dir, item)
        rel_path = os.path.relpath(full_path, rom_root)
        if os.path.isdir(full_path):
            if item == PREVIEW_DIR_NAME:
                continue
            sub_game_count, sub_preview_count = count_games_in_directory(full_path, check_preview=True, recursive=False)
            items.append({
                'name': item,
                'path': rel_path,
                'is_dir': True,
                'size': 0,
                'console': os.path.basename(top_dir) if top_dir else '',
                'preview': None,
                'modified': os.path.getmtime(full_path),
                'game_count': sub_game_count,
                'preview_count': sub_preview_count
            })
        else:
            ext = os.path.splitext(item)[1].lower()
            if detect_system_from_ext(item) == "Unknown" and ext != '.zip':
                continue
            size = os.path.getsize(full_path)
            preview = get_preview_path(full_path)

            name_without_ext = os.path.splitext(item)[0]
            display_name = name_without_ext
            if top_dir in ARCADE_SYSTEMS:
                try:
                    display_name = name_converter.get_arcade_display_name(name_without_ext, lang)
                except Exception as e:
                    print(f"[ERROR] Arcade conversion failed for {name_without_ext}: {e}")
                    display_name = name_without_ext

            pinyin_str = ''
            try:
                pinyin_list = pypinyin.pinyin(display_name, style=Style.FIRST_LETTER)
                pinyin_str = ''.join([p[0] for p in pinyin_list]).lower()
            except Exception as e:
                print(f"[WARN] Pinyin conversion failed for {display_name}: {e}")

            guide_path = os.path.join(os.path.dirname(full_path), name_without_ext + '.txt')
            guide_exists = os.path.exists(guide_path)

            items.append({
                'name': display_name,
                'path': rel_path,
                'is_dir': False,
                'size': size,
                'console': os.path.basename(top_dir) if top_dir else 'Unknown',
                'preview': preview,
                'modified': os.path.getmtime(full_path),
                'guide_exists': guide_exists,
                'pinyin': pinyin_str
            })
    dirs = [i for i in items if i['is_dir']]
    files = [i for i in items if not i['is_dir']]
    dirs.sort(key=lambda x: x['name'].lower())
    files.sort(key=lambda x: x['name'].lower())
    return dirs + files

def delete_game(game_rel_path):
    rom_root = get_rom_root()
    full_path = os.path.join(rom_root, game_rel_path)
    if not os.path.exists(full_path):
        return False
    os.remove(full_path)
    preview = get_preview_path(full_path)
    if preview and os.path.exists(preview):
        os.remove(preview)
    guide = get_guide_path(full_path)
    if guide and os.path.exists(guide):
        os.remove(guide)
    return True

def get_system_version():
    version_files = [
        '/mnt/vendor/oem/version.ini',
        '/etc/version',
        '/etc/os-release'
    ]
    for f in version_files:
        if os.path.exists(f):
            try:
                with open(f, 'r') as file:
                    content = file.read().strip()
                    lines = content.split('\n')
                    for line in lines:
                        if 'version' in line.lower() or 'VERSION' in line:
                            return line.split('=')[-1].strip()
                    return lines[0] if lines else 'Unknown'
            except:
                pass
    return 'Unknown'

def scrape_preview_for_path(game_rel_path: str) -> tuple[bool, str]:
    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, game_rel_path)
    if not os.path.exists(game_full_path):
        return False, "Game file not found"

    top_dir = game_rel_path.split('/')[0]
    system_name = None
    for sys in systems:
        if sys['name'] == top_dir:
            system_name = top_dir
            break
    if system_name is None:
        parent_dir = os.path.basename(os.path.dirname(game_full_path))
        for sys in systems:
            if sys['name'] == parent_dir:
                system_name = parent_dir
                break
    if system_name is None:
        system_name = detect_system_from_ext(os.path.basename(game_full_path))
        if system_name == "Unknown":
            return False, "Cannot determine system for this file"

    system_id = get_system_id(system_name)
    if system_id == -1:
        return False, f"Unknown system: {system_name}"

    if system_name in ["HBMAME", "PGM2", "VARCADE"]:
        system_name = "MAME"
        system_id = get_system_id("MAME")

    game_name = os.path.splitext(os.path.basename(game_full_path))[0]

    if system_name == "PICO":
        try:
            target_dir = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
            os.makedirs(target_dir, exist_ok=True)
            preview_filename = game_name + '.png'
            preview_path = os.path.join(target_dir, preview_filename)
            shutil.copy(game_full_path, preview_path)
            return True, os.path.relpath(preview_path, rom_root)
        except Exception as e:
            return False, f"PICO copy failed: {str(e)}"

    rom_obj = Rom(name=game_name, filename=game_rel_path)
    try:
        crc = scraper.get_crc32_from_file(Path(game_full_path))
        rom_obj.set_crc(crc)
    except Exception as e:
        return False, f"CRC calculation failed: {str(e)}"

    try:
        screenshot_bytes = scraper.scrape_screenshot(
            crc=rom_obj.crc,
            game_name=game_name,
            system_id=system_id,
            system_name=system_name
        )
    except Exception as e:
        return False, f"Scraping failed: {str(e)}"

    if not screenshot_bytes:
        return False, translator.translate("No screenshot found for this game")

    target_dir = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
    os.makedirs(target_dir, exist_ok=True)
    preview_filename = game_name + '.png'
    preview_path = os.path.join(target_dir, preview_filename)

    if scraper.resize:
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(screenshot_bytes))
            img = img.resize((640, 480), Image.LANCZOS)
            img.save(preview_path, 'PNG')
        except Exception as e:
            return False, f"Resize failed: {str(e)}"
    else:
        with open(preview_path, 'wb') as f:
            f.write(screenshot_bytes)

    return True, os.path.relpath(preview_path, rom_root)

# ---------- API routes ----------
@app.route('/api/device_info')
def device_info():
    return jsonify({
        'board': board_info,
        'system_version': get_system_version(),
        'ver': ver
    })

@app.route('/')
def index():
    lang = request.args.get('lang') or system_lang
    translator = Translator(lang)
    return render_template_string(HTML_TEMPLATE, _=translator.translate, lang=lang, ver=ver, systems=systems)

@app.route('/api/sd', methods=['GET', 'POST'])
def handle_sd():
    global current_sd
    if request.method == 'POST':
        data = request.get_json()
        new_sd = data.get('sd')
        if new_sd in (1, 2):
            device.set_sd_storage(new_sd)
            current_sd = device.get_sd_storage()
            return jsonify({'status': 'ok', 'sd': current_sd})
        return jsonify({'error': 'Invalid SD'}), 400
    else:
        return jsonify({'sd': current_sd})

@app.route('/api/dirs')
def api_dirs():
    dirs = get_subdirs()
    print(f"[DEBUG] api_dirs returning {len(dirs)} directories")
    return jsonify(dirs)

@app.route('/api/files')
def api_files():
    subdir = request.args.get('dir', '')
    lang = request.args.get('lang', system_lang)
    if not subdir:
        return jsonify([])
    return jsonify(get_files_in_dir(subdir, lang))

@app.route('/api/preview')
def get_preview():
    path = request.args.get('path')
    if not path:
        return '', 400
    rom_root = get_rom_root()
    full = os.path.join(rom_root, path)
    if not os.path.exists(full):
        return '', 404
    preview = get_preview_path(full)
    if preview and os.path.exists(preview):
        return send_file(preview, mimetype='image/jpeg')
    else:
        return '', 404

@app.route('/api/storage')
def get_storage():
    import shutil
    rom_root = get_rom_root()
    try:
        total, used, free = shutil.disk_usage(rom_root)
        return jsonify({
            'total': total,
            'used': used,
            'free': free,
            'path': rom_root
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_game():
    console = request.form.get('console', '').strip()
    if not console:
        return jsonify({'error': 'Missing console directory'}), 400

    rom_files = request.files.getlist('game_files')
    preview_files = request.files.getlist('preview_file')

    if not rom_files and not preview_files:
        return jsonify({'error': 'No files uploaded'}), 400

    rom_root = get_rom_root()
    base_dir = os.path.join(rom_root, console)
    os.makedirs(base_dir, exist_ok=True)

    saved_roms = []

    if rom_files:
        for rf in rom_files:
            if rf.filename == '':
                continue
            safe_name = safe_filename(rf.filename)
            target_path = os.path.join(base_dir, safe_name)
            if not os.path.abspath(target_path).startswith(os.path.abspath(rom_root)):
                return jsonify({'error': 'Invalid path'}), 400
            rf.save(target_path)
            saved_roms.append(target_path)

    if preview_files:
        preview_dir = os.path.join(base_dir, PREVIEW_DIR_NAME)
        os.makedirs(preview_dir, exist_ok=True)
        for pf in preview_files:
            if pf.filename == '':
                continue
            safe_preview_name = safe_filename(pf.filename)
            preview_path = os.path.join(preview_dir, safe_preview_name)
            pf.save(preview_path)
            saved_roms.append(preview_path)

    return jsonify({
        'success': True,
        'count': len(saved_roms),
        'paths': [os.path.relpath(p, rom_root) for p in saved_roms]
    })

@app.route('/api/delete_preview', methods=['DELETE'])
def delete_preview():
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Missing game path'}), 400

    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, path)
    if not os.path.exists(game_full_path):
        return jsonify({'error': 'Game file not found'}), 404

    preview_path = get_preview_path(game_full_path)
    if not preview_path or not os.path.exists(preview_path):
        return jsonify({'error': 'Preview image not found'}), 404

    try:
        os.remove(preview_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_guide', methods=['DELETE'])
def delete_guide():
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Missing game path'}), 400

    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, path)
    if not os.path.exists(game_full_path):
        return jsonify({'error': 'Game file not found'}), 404

    guide_path = get_guide_path(game_full_path)
    if not guide_path or not os.path.exists(guide_path):
        return jsonify({'error': 'Guide file not found'}), 404

    try:
        os.remove(guide_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/game', methods=['DELETE'])
def api_delete_game():
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Missing path'}), 400
    if delete_game(path):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Delete failed'}), 500

@app.route('/api/update_preview', methods=['POST'])
def update_preview():
    path = request.form.get('path')
    if not path:
        return jsonify({'error': 'Missing game path'}), 400
    if 'image' not in request.files:
        return jsonify({'error': 'No image file'}), 400
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    ext = os.path.splitext(image_file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return jsonify({'error': 'Unsupported image format'}), 400

    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, path)
    if not os.path.exists(game_full_path):
        return jsonify({'error': 'Game file not found'}), 404

    base_name = os.path.splitext(os.path.basename(game_full_path))[0]
    target_dir = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
    os.makedirs(target_dir, exist_ok=True)

    preview_filename = base_name + ext
    preview_path = os.path.join(target_dir, preview_filename)

    image_file.save(preview_path)

    return jsonify({
        'success': True,
        'preview_path': os.path.relpath(preview_path, rom_root)
    })

@app.route('/api/scrape_preview', methods=['POST'])
def scrape_preview():
    data = request.get_json()
    if not data or 'path' not in data:
        return jsonify({'error': 'Missing game path'}), 400

    success, result = scrape_preview_for_path(data['path'])
    if success:
        return jsonify({'success': True, 'preview_path': result})
    else:
        return jsonify({'error': result}), 500 if 'not found' not in result else 404

@app.route('/api/batch_scrape', methods=['POST'])
def batch_scrape():
    data = request.get_json()
    if not data or 'dir' not in data:
        return jsonify({'error': 'Missing directory'}), 400

    subdir = data['dir']
    if not subdir:
        return jsonify({'error': 'Cannot scrape from root directory'}), 400

    rom_root = get_rom_root()
    target_dir = os.path.join(rom_root, subdir)
    if not os.path.isdir(target_dir):
        return jsonify({'error': 'Directory not found'}), 404

    items = get_files_in_dir(subdir)
    files = [item for item in items if not item['is_dir']]
    to_scrape = [f for f in files if not f['preview']]

    if not to_scrape:
        return jsonify({'success': 0, 'failed': 0, 'message': 'No game needs scraping'})

    top_dir = subdir.split('/')[0]
    system_id = get_system_id(top_dir)
    if system_id == -1:
        return jsonify({'error': f'Unknown system: {top_dir}'}), 400
    system_name = top_dir
    if system_name in ["HBMAME", "PGM2", "VARCADE"]:
        system_name = "MAME"

    success_count = 0
    failed_count = 0

    for file_info in to_scrape:
        game_rel_path = file_info['path']
        game_full_path = os.path.join(rom_root, game_rel_path)
        original_game_name = os.path.splitext(os.path.basename(game_full_path))[0]

        if system_name == "PICO":
            try:
                target_dir_preview = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
                os.makedirs(target_dir_preview, exist_ok=True)
                preview_filename = original_game_name + '.png'
                preview_path = os.path.join(target_dir_preview, preview_filename)
                shutil.copy(game_full_path, preview_path)
                success_count += 1
            except Exception as e:
                print(f"Save preview failed for {original_game_name}: {e}")
                failed_count += 1
            continue

        rom_obj = Rom(name=original_game_name, filename=game_rel_path)
        try:
            crc = scraper.get_crc32_from_file(Path(game_full_path))
            rom_obj.set_crc(crc)
        except Exception as e:
            print(f"CRC calculation failed for {original_game_name}: {e}")
            failed_count += 1
            continue

        try:
            screenshot_bytes = scraper.scrape_screenshot(
                crc=rom_obj.crc,
                game_name=original_game_name,
                system_id=system_id,
                system_name=system_name
            )
        except Exception as e:
            print(f"Scraping error for {original_game_name}: {e}")
            failed_count += 1
            continue

        if not screenshot_bytes:
            failed_count += 1
            continue

        target_dir_preview = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
        os.makedirs(target_dir_preview, exist_ok=True)
        preview_filename = original_game_name + '.png'
        preview_path = os.path.join(target_dir_preview, preview_filename)

        try:
            with open(preview_path, 'wb') as f:
                f.write(screenshot_bytes)
            success_count += 1
        except Exception as e:
            print(f"Save preview failed for {original_game_name}: {e}")
            failed_count += 1

    return jsonify({'success': success_count, 'failed': failed_count})

@app.route('/api/rename', methods=['POST'])
def rename_game():
    data = request.get_json()
    if not data or 'path' not in data or 'new_name' not in data:
        return jsonify({'error': 'Missing path or new_name'}), 400

    old_rel_path = data['path']
    new_name = data['new_name'].strip()
    if not new_name:
        return jsonify({'error': 'Invalid name'}), 400

    if '/' in new_name or '\\' in new_name or new_name.startswith('.') or '..' in new_name:
        return jsonify({'error': 'Invalid name'}), 400

    rom_root = get_rom_root()
    old_full_path = os.path.join(rom_root, old_rel_path)
    if not os.path.exists(old_full_path):
        return jsonify({'error': 'File not found'}), 404

    parent_dir = os.path.basename(os.path.dirname(old_full_path))
    system_name = None
    for sys in systems:
        if sys['name'] == parent_dir:
            system_name = parent_dir
            break
    if system_name is None:
        system_name = detect_system_from_ext(os.path.basename(old_full_path))
        if system_name == "Unknown":
            return jsonify({'error': 'Cannot determine system'}), 400

    if system_name in RENAME_BLACKLIST:
        return jsonify({'error': 'Renaming not supported for this system'}), 403

    old_dir = os.path.dirname(old_full_path)
    old_basename = os.path.basename(old_full_path)
    old_ext = os.path.splitext(old_basename)[1]
    new_basename = new_name + old_ext
    new_full_path = os.path.join(old_dir, new_basename)

    if os.path.exists(new_full_path):
        return jsonify({'error': 'File with this name already exists'}), 409

    try:
        os.rename(old_full_path, new_full_path)
    except Exception as e:
        return jsonify({'error': f'Rename failed: {str(e)}'}), 500

    preview_old = get_preview_path(old_full_path)
    preview_new = None
    if preview_old and os.path.exists(preview_old):
        preview_ext = os.path.splitext(preview_old)[1]
        preview_new = os.path.join(old_dir, PREVIEW_DIR_NAME, new_name + preview_ext)
        os.makedirs(os.path.dirname(preview_new), exist_ok=True)
        try:
            os.rename(preview_old, preview_new)
        except Exception as e:
            print(f"Warning: Failed to rename preview: {e}")
            return jsonify({
                'success': True,
                'new_path': os.path.relpath(new_full_path, rom_root),
                'preview_path': None,
                'warning': 'Preview rename failed'
            })

    new_rel_path = os.path.relpath(new_full_path, rom_root)
    return jsonify({
        'success': True,
        'new_path': new_rel_path,
        'preview_path': os.path.relpath(preview_new, rom_root) if preview_new else None
    })

@app.route('/api/upload_guide', methods=['POST'])
def upload_guide():
    if 'path' not in request.form or 'guide_file' not in request.files:
        return jsonify({'error': 'Missing path or file'}), 400

    game_rel_path = request.form['path']
    guide_file = request.files['guide_file']
    if guide_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not guide_file.filename.lower().endswith('.txt'):
        return jsonify({'error': 'Only .txt files are allowed'}), 400

    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, game_rel_path)
    if not os.path.exists(game_full_path):
        return jsonify({'error': 'Game file not found'}), 404

    game_dir = os.path.dirname(game_full_path)
    game_basename = os.path.splitext(os.path.basename(game_full_path))[0]
    guide_path = os.path.join(game_dir, game_basename + '.txt')

    try:
        guide_file.save(guide_path)
    except Exception as e:
        return jsonify({'error': f'Save failed: {str(e)}'}), 500

    return jsonify({'success': True, 'guide_path': os.path.relpath(guide_path, rom_root)})

@app.route('/api/backup_save', methods=['POST'])
def backup_save():
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        files_to_backup = []
        for pattern in BACKUP_PATHS:
            if '*' in pattern:
                expanded = glob.glob(pattern)
                files_to_backup.extend(expanded)
            else:
                if os.path.exists(pattern):
                    files_to_backup.append(pattern)

        if not files_to_backup:
            return jsonify({'error': 'No save data found to backup'}), 404

        marker_content = f"Anbernic Backup v{ver} created at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        with open(BACKUP_MARKER_FILE, 'w') as f:
            f.write(marker_content)
        files_to_backup.append(BACKUP_MARKER_FILE)

        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
            temp_path = tmp.name

        list_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        for f in files_to_backup:
            list_file.write(f + '\n')
        list_file.close()

        cmd = ['tar', '-zcvf', temp_path, '-T', list_file.name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(list_file.name)

        if result.returncode != 0:
            os.unlink(temp_path)
            return jsonify({'error': f'Backup failed: {result.stderr}'}), 500

        if os.path.exists(BACKUP_FILE):
            os.remove(BACKUP_FILE)
        shutil.move(temp_path, BACKUP_FILE)

        try:
            if os.path.exists(BACKUP_MARKER_FILE):
                os.remove(BACKUP_MARKER_FILE)
        except:
            pass

        return send_file(BACKUP_FILE, as_attachment=True,
                         download_name='save_backup.tar.gz',
                         mimetype='application/gzip')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/restore_save', methods=['POST'])
def restore_save():
    if 'backup_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['backup_file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not file.filename.lower().endswith('.tar.gz') and not file.filename.lower().endswith('.tgz'):
        return jsonify({'error': 'Only .tar.gz files are allowed'}), 400

    with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
        file.save(tmp.name)
        temp_path = tmp.name

    try:
        check_cmd = ['tar', '-tf', temp_path]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            os.unlink(temp_path)
            return jsonify({'error': 'Invalid backup file: cannot read archive'}), 400

        marker_path_in_archive = BACKUP_MARKER_FILE.lstrip('/')
        if marker_path_in_archive not in result.stdout.splitlines():
            os.unlink(temp_path)
            return jsonify({'error': 'Invalid backup file: marker not found'}), 400

        cmd = ['tar', '-xzvf', temp_path, '-C', '/']
        result = subprocess.run(cmd, capture_output=True, text=True)

        os.unlink(temp_path)

        if result.returncode != 0:
            return jsonify({'error': f'Restore failed: {result.stderr}'}), 500

        return jsonify({'success': True, 'message': 'Restore completed successfully'})

    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return jsonify({'error': str(e)}), 500

@app.route('/api/import_batch', methods=['POST'])
def import_batch():
    metadata_file = request.files.get('metadata')
    target_console = request.form.get('target_console', '').strip()
    overwrite = request.form.get('overwrite') == 'true'

    if not metadata_file:
        return jsonify({'error': translator.translate('Please select a metadata file')}), 400
    if not target_console:
        return jsonify({'error': translator.translate('Please select target console')}), 400
    if target_console not in [s['name'] for s in systems]:
        return jsonify({'error': 'Invalid target console'}), 400

    uploaded_files = {}
    file_list = request.files.getlist('files')
    for file_obj in file_list:
        raw_filename = file_obj.filename
        decoded_filename = None
        for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
            try:
                decoded_filename = raw_filename.encode('latin1').decode(encoding)
                break
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
        if decoded_filename is None:
            decoded_filename = raw_filename
        uploaded_files[decoded_filename] = file_obj

    if not uploaded_files:
        return jsonify({'error': 'No source files uploaded'}), 400

    print(f"[DEBUG] Uploaded {len(uploaded_files)} files, first 5: {list(uploaded_files.keys())[:5]}")

    content = metadata_file.read().decode('utf-8', errors='ignore')
    filename = metadata_file.filename.lower()

    success = 0
    failed = 0
    skipped = 0
    success_previews = 0
    failed_details = []

    rom_root = get_rom_root()
    target_dir = os.path.join(rom_root, target_console)
    os.makedirs(target_dir, exist_ok=True)

    def find_file(rel_path):
        if rel_path.startswith('./'):
            rel_path = rel_path[2:]
        if rel_path in uploaded_files:
            return rel_path, uploaded_files[rel_path]
        lower_rel = rel_path.lower()
        for key in uploaded_files.keys():
            if key.lower() == lower_rel:
                return key, uploaded_files[key]
        base_name = os.path.basename(rel_path).lower()
        matches = [k for k in uploaded_files.keys() if os.path.basename(k).lower() == base_name]
        if len(matches) == 1:
            return matches[0], uploaded_files[matches[0]]
        elif len(matches) > 1:
            print(f"[DEBUG] Multiple case-insensitive matches for {rel_path}: {matches}")
            return None, None
        else:
            print(f"[DEBUG] No match for {rel_path} (base: {base_name})")
            return None, None

    if filename.endswith('.xml'):
        try:
            root = ET.fromstring(content)
        except Exception as e:
            return jsonify({'error': f'Invalid XML: {str(e)}'}), 400

        for game in root.findall('game'):
            path_elem = game.find('path')
            if path_elem is None or not path_elem.text:
                failed += 1
                failed_details.append({'file': 'unknown', 'reason': 'Missing path element'})
                continue
            file_rel = path_elem.text.strip()
            found_key, src_file = find_file(file_rel)
            if src_file is None:
                failed += 1
                failed_details.append({'file': file_rel, 'reason': 'File not found in source folder'})
                continue

            dest_file = os.path.join(target_dir, file_rel)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            if not overwrite and os.path.exists(dest_file):
                skipped += 1
            else:
                try:
                    src_file.save(dest_file)
                    success += 1
                except Exception as e:
                    failed += 1
                    failed_details.append({'file': file_rel, 'reason': f'Save error: {str(e)}'})
                    continue

            image_elem = game.find('image')
            if image_elem is not None and image_elem.text:
                image_rel = image_elem.text.strip()
                found_img_key, src_img = find_file(image_rel)
                if src_img is not None:
                    dest_img = os.path.join(target_dir, found_img_key)
                    os.makedirs(os.path.dirname(dest_img), exist_ok=True)
                    if not overwrite and os.path.exists(dest_img):
                        continue
                    try:
                        src_img.save(dest_img)
                        success_previews += 1
                    except Exception as e:
                        print(f"Save preview failed for {image_rel}: {e}")

    elif filename.endswith('.txt'):
        lines = content.splitlines()
        blocks = []
        current_block = []
        for line in lines:
            if line.strip() == '':
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        if current_block:
            blocks.append(current_block)

        for block in blocks:
            has_game = any(line.startswith('game:') for line in block)
            if not has_game:
                continue

            game_name = None
            file_rel = None
            extra_files = []
            assets = {}

            for line in block:
                if line.startswith('game:'):
                    game_name = line[len('game:'):].strip()
                elif line.startswith('file:'):
                    file_rel = line[len('file:'):].strip()
                elif line.startswith('files:'):
                    rest = line[len('files:'):].strip()
                    if rest:
                        extra_files.append(rest)
                elif line.startswith('assets.'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        key = key.strip()
                        val = val.strip()
                        assets[key] = val

            if not file_rel and extra_files:
                file_rel = extra_files[0]

            if not game_name or not file_rel:
                failed += 1
                failed_details.append({'file': 'unknown', 'reason': 'Missing game or file field'})
                continue

            found_key, src_file = find_file(file_rel)
            if src_file is None:
                failed += 1
                failed_details.append({'file': file_rel, 'reason': 'File not found in source folder'})
                continue

            dest_file = os.path.join(target_dir, file_rel)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            if not overwrite and os.path.exists(dest_file):
                skipped += 1
            else:
                try:
                    src_file.save(dest_file)
                    success += 1
                except Exception as e:
                    failed += 1
                    failed_details.append({'file': file_rel, 'reason': f'Save error: {str(e)}'})
                    continue

            preview_path_candidates = []
            for asset_key in ['assets.box_front', 'assets.boxfront', 'assets.cover', 'assets.logo']:
                if asset_key in assets:
                    preview_path_candidates.append(assets[asset_key])
            if not preview_path_candidates:
                media_prefix = f"media/{game_name}/"
                file_base = os.path.splitext(os.path.basename(file_rel))[0]
                alt_media_prefix = f"media/{file_base}/"
                img_names = ['boxFront.jpg', 'boxFront.png', 'cover.jpg', 'cover.png', 'folder.jpg', 'front.jpg']
                for prefix in [media_prefix, alt_media_prefix]:
                    for img_name in img_names:
                        preview_path_candidates.append(prefix + img_name)

            found_img = None
            found_img_key = None
            for candidate in preview_path_candidates:
                fk, src_img = find_file(candidate)
                if src_img is not None:
                    found_img = candidate
                    found_img_key = fk
                    break

            if found_img and found_img_key:
                base_name = os.path.splitext(os.path.basename(file_rel))[0]
                ext = os.path.splitext(found_img)[1]
                dest_img_dir = os.path.join(target_dir, PREVIEW_DIR_NAME)
                os.makedirs(dest_img_dir, exist_ok=True)
                dest_img = os.path.join(dest_img_dir, base_name + ext)
                if not overwrite and os.path.exists(dest_img):
                    continue
                try:
                    src_img = uploaded_files.get(found_img_key)
                    if src_img is not None:
                        src_img.save(dest_img)
                        success_previews += 1
                except Exception as e:
                    print(f"Save preview failed for {found_img}: {e}")
            else:
                print(f"Preview not found for game: {game_name}")

    else:
        return jsonify({'error': 'Unsupported metadata format'}), 400

    return jsonify({
        'success': success,
        'failed': failed,
        'skipped': skipped,
        'failed_details': failed_details,
        'message': translator.translate('Import completed!\nSuccess: {success}, Failed: {failed}, Skipped: {skipped}, Preview: {success_previews}.').format(success=success, failed=failed, skipped=skipped, success_previews=success_previews)
    })

def normalize_path(path):
    path = path.strip()
    path = path.replace('\\', '/')
    if path.startswith('./'):
        path = path[2:]
    if path.startswith('/'):
        path = path[1:]
    return path

@app.route('/api/import_analyze', methods=['POST'])
def import_analyze():
    metadata_file = request.files.get('metadata')
    target_console = request.form.get('target_console', '').strip()
    use_display_name = request.form.get('use_display_name', 'false').lower() == 'true'

    if not metadata_file:
        return jsonify({'error': translator.translate('Please select a metadata file')}), 400
    if not target_console:
        return jsonify({'error': translator.translate('Please select target console')}), 400
    if target_console not in [s['name'] for s in systems]:
        return jsonify({'error': 'Invalid target console'}), 400

    if target_console in ARCADE_SYSTEMS:
        use_display_name = False

    content = metadata_file.read().decode('utf-8', errors='ignore')
    filename = metadata_file.filename.lower()
    file_list = []
    preview_list = []

    if filename.endswith('.xml'):
        try:
            root = ET.fromstring(content)
        except Exception as e:
            return jsonify({'error': f'Invalid XML: {str(e)}'}), 400
        for game in root.findall('game'):
            path_elem = game.find('path')
            if path_elem is None or not path_elem.text:
                continue
            game_rel_path = normalize_path(path_elem.text.strip())

            display_name = None
            if use_display_name:
                name_elem = game.find('name')
                if name_elem is not None and name_elem.text:
                    display_name = name_elem.text.strip()
                else:
                    display_name = os.path.splitext(os.path.basename(game_rel_path))[0]

            target_game_path = game_rel_path
            if display_name:
                ext = os.path.splitext(game_rel_path)[1]
                target_game_path = os.path.join(os.path.dirname(game_rel_path), display_name + ext)
                target_game_path = target_game_path.replace('\\', '/')

            file_list.append({
                'source': game_rel_path,
                'target': target_game_path
            })

            game_dir = os.path.dirname(game_rel_path)
            game_base = os.path.basename(game_rel_path)
            game_name_without_ext = os.path.splitext(game_base)[0]

            image_elem = game.find('image')
            if image_elem is None or not image_elem.text:
                image_elem = game.find('boxart')
            if image_elem is not None and image_elem.text:
                img_source = normalize_path(image_elem.text.strip())
                ext = os.path.splitext(img_source)[1]
                if not ext:
                    ext = '.png'
                if display_name:
                    target_filename = display_name + ext
                else:
                    target_filename = game_name_without_ext + ext
                if game_dir:
                    target_path = os.path.join(game_dir, 'Imgs', target_filename)
                else:
                    target_path = os.path.join('Imgs', target_filename)
                target_path = target_path.replace('\\', '/')
                preview_list.append({
                    'source': img_source,
                    'target': target_path,
                    'game_path': game_rel_path,
                    'display_name': display_name
                })
    elif filename.endswith('.txt'):
        lines = content.splitlines()
        blocks = []
        current_block = []
        for line in lines:
            if line.strip() == '':
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        if current_block:
            blocks.append(current_block)

        for block in blocks:
            has_game = any(line.startswith('game:') for line in block)
            if not has_game:
                continue
            game_name = None
            file_rel = None
            extra_files = []
            assets = {}
            for line in block:
                if line.startswith('game:'):
                    game_name = line[len('game:'):].strip()
                elif line.startswith('file:'):
                    file_rel = normalize_path(line[len('file:'):].strip())
                elif line.startswith('files:'):
                    rest = normalize_path(line[len('files:'):].strip())
                    if rest:
                        extra_files.append(rest)
                elif line.startswith('assets.'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        assets[key.strip()] = normalize_path(val.strip())

            if not file_rel and extra_files:
                file_rel = extra_files[0]

            if not game_name or not file_rel:
                continue

            display_name = None
            if use_display_name:
                display_name = game_name
                if not display_name:
                    display_name = os.path.splitext(os.path.basename(file_rel))[0]

            target_game_path = file_rel
            if display_name:
                ext = os.path.splitext(file_rel)[1]
                target_game_path = os.path.join(os.path.dirname(file_rel), display_name + ext)
                target_game_path = target_game_path.replace('\\', '/')

            file_list.append({
                'source': file_rel,
                'target': target_game_path
            })

            base_name = os.path.splitext(os.path.basename(file_rel))[0]

            preview_candidates = []
            for asset_key in ['assets.box_front', 'assets.boxfront', 'assets.cover', 'assets.logo']:
                if asset_key in assets:
                    preview_candidates.append(assets[asset_key])
            if not preview_candidates:
                media_prefix = f"media/{base_name}/"
                for img_name in ['boxFront.jpg', 'boxFront.png', 'cover.jpg', 'cover.png', 'folder.jpg']:
                    preview_candidates.append(media_prefix + img_name)

            for source_path in preview_candidates:
                ext = os.path.splitext(source_path)[1]
                if not ext:
                    ext = '.png'
                if display_name:
                    target_filename = display_name + ext
                else:
                    target_filename = base_name + ext
                target_path = f"Imgs/{target_filename}"
                preview_list.append({
                    'source': source_path,
                    'target': target_path,
                    'game_path': file_rel,
                    'display_name': display_name
                })
    else:
        return jsonify({'error': 'Unsupported metadata format'}), 400

    return jsonify({
        'files': file_list,
        'previews': preview_list,
        'count': len(file_list) + len(preview_list)
    })

@app.route('/api/upload_single', methods=['POST'])
def upload_single():
    target_console = request.form.get('target_console', '').strip()
    relative_path = request.form.get('relative_path', '').strip()
    overwrite = request.form.get('overwrite') == 'true'

    if not target_console or not relative_path:
        return jsonify({'error': 'Missing target_console or relative_path'}), 400
    if target_console not in [s['name'] for s in systems]:
        return jsonify({'error': 'Invalid target console'}), 400
    if '..' in relative_path or relative_path.startswith('/'):
        return jsonify({'error': 'Invalid relative path'}), 400

    file_obj = request.files.get('file')
    if not file_obj:
        return jsonify({'error': 'No file uploaded'}), 400

    rom_root = get_rom_root()
    dest_dir = os.path.join(rom_root, target_console)
    dest_full_path = os.path.join(dest_dir, relative_path)

    if not os.path.abspath(dest_full_path).startswith(os.path.abspath(rom_root)):
        return jsonify({'error': 'Invalid path'}), 400

    os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)

    if not overwrite and os.path.exists(dest_full_path):
        return jsonify({'error': 'File already exists', 'skipped': True}), 200

    try:
        file_obj.save(dest_full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Save failed: {str(e)}'}), 500

@app.route('/shutdown', methods=['GET'])
def shutdown():
    import threading
    import time
    import os

    def force_exit():
        time.sleep(0.3)
        os._exit(0)

    threading.Thread(target=force_exit).start()
    return "服务器正在关闭...", 200

# ---------- Load HTML ----------
base_path = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(base_path, "web", "template.html")
if os.path.exists(html_path):
    with open(html_path, 'r') as f:
        HTML_TEMPLATE = f.read()
else:
    print(f'缺少文件: template.html，正在退出...')
    os._exit(0)

def exit_on_key():
    print("[DEBUG] 按键监听线程已启动，按 SELECT 退出")
    while True:
        input.check()
        if input.key("SELECT"):
            print(f"[DEBUG] 检测到按键: {input.codeName}，正在退出...")
            os._exit(0)

def load_menu() -> int:

    menu_selected_position = 0
    all_menu = [
        translator.translate("Manage via Browser"),
        translator.translate("Manage on Device")
    ]
    x_size, y_size, max_elem = screen_resolutions.get(hw_info, (640, 480, 11))
    button_x = x_size - 120
    button_y = y_size - 30


    while True:
        if input.key("DY"):
            menu_selected_position = (menu_selected_position + input.value) % len(all_menu)
        elif input.key("A"):
            return menu_selected_position
        elif input.key("MENUF"):
            gr.draw_clear()
            gr.draw_log(
                f"{translator.translate('Exiting...')}", fill=gr.colorBlue, outline=gr.colorBlueD1
            )
            gr.draw_paint()
            time.sleep(1.5)
            gr.draw_end()
            sys.exit(0)

        gr.draw_clear()

        gr.draw_rectangle_r([10, 100, x_size - 10, y_size - 40], 15, fill=gr.colorGrayD2, outline=None)

        gr.draw_text((x_size / 2, 40), f"{translator.translate('Anbernic Game Manager')} v{ver}", font=32, anchor="mm")
        gr.draw_text((x_size / 2, 80), f"{translator.translate('Model')}: {board_info}", font=23, anchor="mm")

        btn_width = int(x_size * 0.6)
        btn_height = int(y_size * 0.15)
        btn_width = max(btn_width, 200)
        btn_height = max(btn_height, 60)

        spacing = int(btn_height * 0.3)
        total_height = 2 * btn_height + spacing

        y_start = 110
        y_end = button_y - 40
        available_height = y_end - y_start

        if available_height < total_height:
            btn_height = int((available_height - spacing) / 2)
            btn_height = max(btn_height, 50)
            total_height = 2 * btn_height + spacing

        y_center = (y_start + y_end) // 2
        first_btn_y = y_center - total_height // 2
        second_btn_y = first_btn_y + btn_height + spacing

        btn_x = (x_size - btn_width) // 2

        selected = menu_selected_position
        for i, menu_key in enumerate(all_menu):
            y_pos = first_btn_y if i == 0 else second_btn_y
            fill_color = gr.colorBlue if i == selected else gr.colorGrayL1
            gr.draw_rectangle_r(
                [btn_x, y_pos, btn_x + btn_width, y_pos + btn_height],
                10,
                fill=fill_color,
                outline=None
            )
            gr.draw_text(
                (btn_x + btn_width / 2, y_pos + btn_height / 2),
                translator.translate(menu_key),
                font=21,
                anchor="mm"
            )

        gr.button_circle((30, button_y), "A", f"{translator.translate('Confirm')}")
        gr.button_circle((button_x, button_y), "M", f"{translator.translate('Exit')}")
        gr.draw_paint()
        input.check()
        time.sleep(0.05)

def main():
    if load_menu() == 1:
        print("  正在启动本机端...")
        from local_ui import main as local_main
        local_main()
        return

    if not is_connected():
        show_error_screen()
        time.sleep(3)
        sys.exit(1)

    ip = get_local_ip()
    print("\n" + "="*50)
    print("  🎮 Anbernic 游戏管理器已启动")
    print("="*50)
    print(f"  访问地址: http://{ip}:5000")
    print(f"  本机地址: http://127.0.0.1:5000")
    print("  关闭服务: 按 Ctrl+C 或访问 /shutdown")
    print("="*50 + "\n")
    show_splash_screen(ip)

    rom_root = get_rom_root()
    print(f"[DEBUG] ROM root path: {rom_root}")
    if os.path.exists(rom_root):
        print(f"[DEBUG] Content of ROM root: {os.listdir(rom_root)}")
    else:
        print(f"[DEBUG] ROM root does not exist!")

    threading.Thread(target=exit_on_key, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()