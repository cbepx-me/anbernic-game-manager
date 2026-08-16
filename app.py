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

# 导入你的已有模块
from scraper import Scraper, Rom
from systems import systems, get_system_id
from anbernic import Anbernic
from language import Translator
from name_converter import name_converter

# 版本
ver = "1.1.2"

# 全局设备信息
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
    import sdl2.ext
    from PIL import Image, ImageDraw, ImageFont
    SDL_AVAILABLE = True
except ImportError:
    SDL_AVAILABLE = False

scraper = Scraper()
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_path):
    scraper.load_config_from_json(config_path)
else:
    print("Warning: config.json not found, scraper may not work.")

import input

try:
    lang_info = Path("/mnt/vendor/oem/language.ini").read_text().splitlines()[0]
    system_list = ['zh_CN', 'zh_TW', 'en_US', 'ja_JP', 'ko_KR', 'es_LA', 'ru_RU', 'de_DE', 'fr_FR', 'pt_BR']
    system_lang = system_list[int(lang_info)]
except (FileNotFoundError, IndexError):
    system_lang = 'en_US'


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
    """使用 graphic.py 中的 UserInterface 显示启动画面"""
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

        # 标题
        title = f'★ {translator.translate("Anbernic game management")} ★'
        ui.draw_text((ui.screen_width // 2, box_y + 50), title, font=32, color="#ffffff", anchor="mm")

        # URL
        url_text = f"http://{ip}:5000"
        ui.draw_text((ui.screen_width // 2, box_y + 100), url_text, font=32, color="#00d7ff", anchor="mm")

        # 二维码
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
            # 缺少 qrcode 库，显示提示
            print((ui.screen_width // 2, box_y + 190), "QR code library not installed")

        # 引导文字（二维码下方或替代）
        if qr_success:
            qr_text = translator.translate("Scan QR code or visit the URL above")
            ui.draw_text((ui.screen_width // 2, box_y + 320), qr_text, font=25, color="#ffd700", anchor="mm")
        else:
            # 无二维码时，提示直接访问URL
            open_text = translator.translate("Open this address in your browser")
            ui.draw_text((ui.screen_width // 2, box_y + 230), open_text, font=25, color="#ffd700", anchor="mm")

        # 底部操作提示
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

# ---------- 获取本机 IP ----------
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

# ---------- Flask 应用 ----------
app = Flask(__name__)

# 设置上传文件大小限制（1GB）
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

# 配置
ALLOWED_IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
PREVIEW_DIR_NAME = "Imgs"

device = Anbernic()
translator = Translator(system_lang)
ARCADE_SYSTEMS = {
    "ATOMISWAVE", "CPS1", "CPS2", "CPS3", "FBNEO",
    "HBMAME", "MAME", "NAOMI", "NEOGEO", "OEM_GAME", "PGM2", "VARCADE"
}
RENAME_BLACKLIST = ARCADE_SYSTEMS | {"DOS", "EASYRPG", "ONS", "SCUMMVM"}
current_sd = 1  # 默认使用 SD1

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

def safe_filename(filename):
    """
    安全处理文件名：保留 Unicode（中文等），仅移除路径分隔符和 '..'，
    防止目录遍历攻击。
    """
    # 替换路径分隔符
    filename = filename.replace('/', '_').replace('\\', '_')
    # 移除 '..' 防止目录遍历
    while '..' in filename:
        filename = filename.replace('..', '_')
    # 移除控制字符（ASCII < 32）
    filename = ''.join(c for c in filename if ord(c) >= 32)
    # 去除首尾空白
    filename = filename.strip()
    # 如果文件名为空，给一个默认名
    if not filename:
        filename = 'unnamed'
    return filename

def get_rom_root():
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
    for sys in systems:
        if ext in sys["extensions"]:
            return sys["name"]
    return "Unknown"

def get_subdirs():
    rom_root = get_rom_root()
    if not os.path.isdir(rom_root):
        print(f"[DEBUG] ROM root {rom_root} is not a directory")
        return []
    dirs = []
    for item in os.listdir(rom_root):
        if item in ["APPS", "PORTS", "EASYRPG", "ONS"]:
            continue
        full = os.path.join(rom_root, item)
        if os.path.isdir(full) and not item.startswith('.') and item != PREVIEW_DIR_NAME:
            game_count, preview_count = count_games_in_directory(full)
            dirs.append({
                'name': item,
                'path': item,
                'has_games': game_count > 0,
                'game_count': game_count,
                'preview_count': preview_count
            })
    dirs.sort(key=lambda x: x['name'].lower())
    print(f"[DEBUG] get_subdirs found {len(dirs)} directories")
    return dirs

def count_games_in_directory(dir_path):
    """
    统计指定目录下的游戏文件数量和拥有预览图的游戏数量（递归）。
    返回 (game_count, preview_count)
    """
    game_count = 0
    preview_count = 0
    for root, _, files in os.walk(dir_path):
        # 跳过 Imgs 目录
        if PREVIEW_DIR_NAME in root.split(os.sep):
            continue
        for f in files:
            if f.startswith('.'):
                continue
            # 检测是否为游戏文件（扩展名匹配）
            if detect_system_from_ext(f) != "Unknown" or f.endswith('.zip'):
                game_count += 1
                # 检查是否有预览图
                game_path = os.path.join(root, f)
                if get_preview_path(game_path) is not None:
                    preview_count += 1
    return game_count, preview_count

def get_files_in_dir(subdir, lang=None):
    """
    返回指定目录下的子目录和文件（不递归）。
    subdir 可以是 ''（根目录）、'NES' 或 'NES/子目录' 等。
    """
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
            # 忽略 Imgs 目录
            if item == PREVIEW_DIR_NAME:
                continue
            sub_game_count, sub_preview_count = count_games_in_directory(full_path)
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
            # 仅识别支持的游戏扩展名
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
                'guide_exists': guide_exists
            })
    # 目录在前，文件在后，各自按名称排序
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
    """尝试从常见文件读取系统版本"""
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

# ---------- API 路由 ----------
@app.route('/api/device_info')
def device_info():
    return jsonify({
        'board': board_info,
        'system_version': get_system_version(),
        'ver': ver
    })

from flask import render_template_string
@app.route('/')
def index():
    lang = request.args.get('lang') or system_lang
    translator = Translator(lang)
    return render_template_string(HTML_TEMPLATE, _=translator.translate, lang=lang, ver=ver)

@app.route('/api/sd', methods=['GET', 'POST'])
def handle_sd():
    global current_sd
    if request.method == 'POST':
        data = request.get_json()
        new_sd = data.get('sd')
        if new_sd in (1, 2):
            current_sd = new_sd
            device.set_sd_storage(new_sd)
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
    """获取当前 SD 卡的存储空间信息"""
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
            # 防止路径穿越
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

    # 查找预览图
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
    """更新预览图：自动重命名并覆盖已有文件"""
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

    # 生成预览图文件名（与游戏主名相同）
    base_name = os.path.splitext(os.path.basename(game_full_path))[0]
    target_dir = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
    os.makedirs(target_dir, exist_ok=True)

    preview_filename = base_name + ext
    preview_path = os.path.join(target_dir, preview_filename)

    # 保存文件（直接覆盖）
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

    game_rel_path = data['path']
    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, game_rel_path)
    if not os.path.exists(game_full_path):
        return jsonify({'error': 'Game file not found'}), 404

    # 1. 确定系统名称：优先从顶层目录名推断
    top_dir = game_rel_path.split('/')[0]
    system_name = None
    for sys in systems:
        if sys['name'] == top_dir:
            system_name = top_dir
            break

    if system_name is None:
        # 如果顶层目录不在 systems 中，再尝试父目录（兼容子目录结构）
        parent_dir = os.path.basename(os.path.dirname(game_full_path))
        for sys in systems:
            if sys['name'] == parent_dir:
                system_name = parent_dir
                break

    if system_name is None:
        # 最后回退到扩展名检测
        system_name = detect_system_from_ext(os.path.basename(game_full_path))
        if system_name == "Unknown":
            return jsonify({'error': 'Cannot determine system for this file'}), 400

    system_id = get_system_id(system_name)
    if system_id == -1:
        return jsonify({'error': f'Unknown system: {system_name}'}), 400

    # 修正 HBMAME/PGM2/VARCADE → MAME
    if system_name in ["HBMAME", "PGM2", "VARCADE"]:
        system_name = "MAME"
        system_id = get_system_id("MAME")

    # 2. 获取游戏原始名称（不含扩展名）
    game_name = os.path.splitext(os.path.basename(game_full_path))[0]

    if system_name == "PICO":
        try:
            target_dir = os.path.join(os.path.dirname(game_full_path), PREVIEW_DIR_NAME)
            os.makedirs(target_dir, exist_ok=True)
            preview_filename = game_name + '.png'
            preview_path = os.path.join(target_dir, preview_filename)
            shutil.copy(game_full_path, preview_path)
        except Exception as e:
            return jsonify({'error': f'Scraping failed: {str(e)}'}), 500
        return jsonify({
        'success': True,
        'preview_path': os.path.relpath(preview_path, rom_root)
    })

    # 3. 计算 CRC
    rom_obj = Rom(name=game_name, filename=game_rel_path)
    try:
        crc = scraper.get_crc32_from_file(Path(game_full_path))
        rom_obj.set_crc(crc)
    except Exception as e:
        return jsonify({'error': f'Failed to calculate CRC: {str(e)}'}), 500

    # 4. 执行刮削
    try:
        screenshot_bytes = scraper.scrape_screenshot(
            crc=rom_obj.crc,
            game_name=game_name,
            system_id=system_id,
            system_name=system_name
        )
    except Exception as e:
        return jsonify({'error': f'Scraping failed: {str(e)}'}), 500

    if not screenshot_bytes:
        return jsonify({'error': f'{translator.translate("No screenshot found for this game")}'}), 404

    # 5. 保存预览图（使用原始文件名）
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
            return jsonify({'error': f'Failed to resize image: {str(e)}'}), 500
    else:
        with open(preview_path, 'wb') as f:
            f.write(screenshot_bytes)

    return jsonify({
        'success': True,
        'preview_path': os.path.relpath(preview_path, rom_root)
    })

@app.route('/api/batch_scrape', methods=['POST'])
def batch_scrape():
    """批量刮削当前目录下所有游戏封面"""
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

    # 获取目录下所有游戏文件（排除子目录和已有预览的）
    items = get_files_in_dir(subdir)
    files = [item for item in items if not item['is_dir']]
    to_scrape = [f for f in files if not f['preview']]

    if not to_scrape:
        return jsonify({'success': 0, 'failed': 0, 'message': 'No game needs scraping'})

    # 🔥 关键修复：提取第一级目录作为系统名
    top_dir = subdir.split('/')[0]   # 例如 "GBA/Subdir" → "GBA"
    system_id = get_system_id(top_dir)
    if system_id == -1:
        # 如果顶级目录不在 systems 列表中，则尝试用扩展名检测（但通常不会发生）
        # 这里报错提示用户
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

        # 计算 CRC
        rom_obj = Rom(name=original_game_name, filename=game_rel_path)
        try:
            crc = scraper.get_crc32_from_file(Path(game_full_path))
            rom_obj.set_crc(crc)
        except Exception as e:
            print(f"CRC calculation failed for {original_game_name}: {e}")
            failed_count += 1
            continue

        # 调用刮削
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

        # 保存预览图
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

    # 安全过滤：只允许字母、数字、空格、下划线、连字符、中文等，但简单起见用 safe_filename 的反向？
    # 但我们需要保留新名称中的合法字符，不允许路径分隔符
    if '/' in new_name or '\\' in new_name or new_name.startswith('.') or '..' in new_name:
        return jsonify({'error': 'Invalid name'}), 400

    rom_root = get_rom_root()
    old_full_path = os.path.join(rom_root, old_rel_path)
    if not os.path.exists(old_full_path):
        return jsonify({'error': 'File not found'}), 404

    # 检查系统是否允许重命名
    # 先获取系统名：从目录名推断
    parent_dir = os.path.basename(os.path.dirname(old_full_path))
    system_name = None
    for sys in systems:
        if sys['name'] == parent_dir:
            system_name = parent_dir
            break
    if system_name is None:
        # 回退到扩展名检测（但一般不会）
        system_name = detect_system_from_ext(os.path.basename(old_full_path))
        if system_name == "Unknown":
            return jsonify({'error': 'Cannot determine system'}), 400

    if system_name in RENAME_BLACKLIST:
        return jsonify({'error': 'Renaming not supported for this system'}), 403

    # 获取旧文件名信息
    old_dir = os.path.dirname(old_full_path)
    old_basename = os.path.basename(old_full_path)
    old_ext = os.path.splitext(old_basename)[1]  # 包括点，如 '.zip'
    # 新完整文件名
    new_basename = new_name + old_ext
    new_full_path = os.path.join(old_dir, new_basename)

    # 检查新文件是否已存在
    if os.path.exists(new_full_path):
        return jsonify({'error': 'File with this name already exists'}), 409

    # 重命名 ROM 文件
    try:
        os.rename(old_full_path, new_full_path)
    except Exception as e:
        return jsonify({'error': f'Rename failed: {str(e)}'}), 500

    # 重命名预览图（如果存在）
    preview_old = get_preview_path(old_full_path)  # 返回完整路径
    preview_new = None
    if preview_old and os.path.exists(preview_old):
        # 获取预览图的扩展名
        preview_ext = os.path.splitext(preview_old)[1]  # 如 .png
        preview_new = os.path.join(old_dir, PREVIEW_DIR_NAME, new_name + preview_ext)
        # 确保 Imgs 目录存在
        os.makedirs(os.path.dirname(preview_new), exist_ok=True)
        try:
            os.rename(preview_old, preview_new)
        except Exception as e:
            # 如果预览图重命名失败，但 ROM 已重命名，记录日志，返回部分成功
            print(f"Warning: Failed to rename preview: {e}")
            # 我们仍可返回成功，但提示预览未更新
            # 此处我们返回成功但附带警告
            return jsonify({
                'success': True,
                'new_path': os.path.relpath(new_full_path, rom_root),
                'preview_path': None,
                'warning': 'Preview rename failed'
            })

    # 返回新路径
    new_rel_path = os.path.relpath(new_full_path, rom_root)
    return jsonify({
        'success': True,
        'new_path': new_rel_path,
        'preview_path': os.path.relpath(preview_new, rom_root) if preview_new else None
    })

@app.route('/api/upload_guide', methods=['POST'])
def upload_guide():
    """上传攻略文件（.txt）到游戏所在目录，并命名为 游戏主名.txt"""
    if 'path' not in request.form or 'guide_file' not in request.files:
        return jsonify({'error': 'Missing path or file'}), 400

    game_rel_path = request.form['path']
    guide_file = request.files['guide_file']
    if guide_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # 检查扩展名
    if not guide_file.filename.lower().endswith('.txt'):
        return jsonify({'error': 'Only .txt files are allowed'}), 400

    rom_root = get_rom_root()
    game_full_path = os.path.join(rom_root, game_rel_path)
    if not os.path.exists(game_full_path):
        return jsonify({'error': 'Game file not found'}), 404

    # 构建攻略文件路径
    game_dir = os.path.dirname(game_full_path)
    game_basename = os.path.splitext(os.path.basename(game_full_path))[0]
    guide_path = os.path.join(game_dir, game_basename + '.txt')

    # 保存文件（覆盖已有）
    try:
        guide_file.save(guide_path)
    except Exception as e:
        return jsonify({'error': f'Save failed: {str(e)}'}), 500

    return jsonify({'success': True, 'guide_path': os.path.relpath(guide_path, rom_root)})

@app.route('/api/backup_save', methods=['POST'])
def backup_save():
    """备份存档：打包指定目录为 tar.gz 并下载"""
    try:
        # 确保备份目录存在
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # 收集实际存在的文件/目录
        files_to_backup = []
        for pattern in BACKUP_PATHS:
            # 如果包含通配符，用 glob 展开
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

        # 使用临时文件，避免下载失败时破坏原有备份
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
            temp_path = tmp.name

        # 构建 tar 命令：使用 -T 选项从文件列表读取
        # 创建一个临时文件列表
        list_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        for f in files_to_backup:
            list_file.write(f + '\n')
        list_file.close()

        # 执行 tar
        cmd = ['tar', '-zcvf', temp_path, '-T', list_file.name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(list_file.name)  # 删除临时列表文件

        if result.returncode != 0:
            os.unlink(temp_path)
            return jsonify({'error': f'Backup failed: {result.stderr}'}), 500

        # 将临时文件移动到正式位置（可选）
        # 如果已存在，覆盖
        if os.path.exists(BACKUP_FILE):
            os.remove(BACKUP_FILE)
        shutil.move(temp_path, BACKUP_FILE)

        try:
            if os.path.exists(BACKUP_MARKER_FILE):
                os.remove(BACKUP_MARKER_FILE)
        except:
            pass

        # 发送文件下载
        return send_file(BACKUP_FILE, as_attachment=True,
                         download_name='save_backup.tar.gz',
                         mimetype='application/gzip')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/restore_save', methods=['POST'])
def restore_save():
    """恢复存档：上传 tar.gz 文件并解压到根目录"""
    if 'backup_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['backup_file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # 检查扩展名
    if not file.filename.lower().endswith('.tar.gz') and not file.filename.lower().endswith('.tgz'):
        return jsonify({'error': 'Only .tar.gz files are allowed'}), 400

    # 保存上传的文件到临时位置
    with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
        file.save(tmp.name)
        temp_path = tmp.name

    try:
        # 第一步：检查标记文件是否存在
        # 使用 tar -tf 列出文件列表，查找标记文件
        check_cmd = ['tar', '-tf', temp_path]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            os.unlink(temp_path)
            return jsonify({'error': 'Invalid backup file: cannot read archive'}), 400

        # 检查标记文件是否在列表中（注意：路径是绝对路径，如 /tmp/anbernic_backup_marker）
        marker_path_in_archive = BACKUP_MARKER_FILE.lstrip('/')
        if marker_path_in_archive not in result.stdout.splitlines():
            os.unlink(temp_path)
            return jsonify({'error': 'Invalid backup file: marker not found'}), 400

        # 解压到根目录（注意：备份时使用绝对路径，解压后覆盖对应位置）
        # 使用 -xvf 解压，-C / 指定根目录
        cmd = ['tar', '-xzvf', temp_path, '-C', '/']
        result = subprocess.run(cmd, capture_output=True, text=True)

        # 删除临时文件
        os.unlink(temp_path)

        if result.returncode != 0:
            return jsonify({'error': f'Restore failed: {result.stderr}'}), 500

        return jsonify({'success': True, 'message': 'Restore completed successfully'})

    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return jsonify({'error': str(e)}), 500

@app.route('/shutdown', methods=['GET'])
def shutdown():
    import threading
    import time
    import os

    def force_exit():
        # 等待 0.3 秒，确保 HTTP 响应已经发送到客户端
        time.sleep(0.3)
        # 强制退出进程，不执行任何清理（在嵌入式设备上安全）
        os._exit(0)

    # 启动后台线程执行退出
    threading.Thread(target=force_exit).start()
    return "服务器正在关闭...", 200

# ---------- 前端 HTML ----------
base_path = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(base_path, "web", "template.html")
if os.path.exists(html_path):
    with open(html_path, 'r') as f:
        HTML_TEMPLATE = f.read()
else:
    print(f'缺少文件: template.html，正在退出...')
    os._exit(0)

def exit_on_key():
    """后台线程：监听任意物理按键，按下即退出程序"""
    print("[DEBUG] 按键监听线程已启动，按 SELECT 退出")
    while True:
        input.check()  # 阻塞等待按键事件
        if input.key("SELECT"):
            print(f"[DEBUG] 检测到按键: {input.codeName}，正在退出...")
            os._exit(0)  # 直接退出，避免调用路由

def main():
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

    # 启动 Flask
    app.run(host='0.0.0.0', port=5000, debug=False)

# ---------- 启动 ----------
if __name__ == '__main__':
    main()