#!/usr/bin/env python3

import os
import sys
import time
from pathlib import Path

base_path = os.path.dirname(os.path.abspath(__file__))
deps_path = os.path.join(base_path, "deps")
if os.path.isdir(deps_path):
    sys.path.insert(0, deps_path)

import app
import input
from graphic import UserInterface
from app import (
    get_files_in_dir, get_subdirs, delete_game,
    scrape_preview_for_path, system_lang
)

from language import Translator
from anbernic import Anbernic

class LocalUI:
    def __init__(self):
        self.ui = UserInterface()
        self.an = Anbernic()
        self.current_path = ""
        self.current_items = []
        self.selected_index = 0
        self.dir_memory = {"root": 0, "sub": {}}
        self.scroll_offset = 0
        self.current_file = None
        self.running = True
        self.mode = "browse"
        app.current_sd = self.an.get_sd_storage()

        self.menu_options = []
        self.menu_index = 0
        self.dir_cache = {}
        self.file_cache = {}

        self.lang = Translator(system_lang)
        self.max_display = self.ui.max_elem
        self.screen_width = self.ui.screen_width
        self.screen_height = self.ui.screen_height

        self.colors = {
            'bg': '#1a1a2e',
            'bg_list': '#1e1e30',
            'item_normal': '#383838',
            'item_selected': '#0072bb',
            'text': '#ffffff',
            'text_secondary': '#a6adc8',
            'text_dim': '#6c7086',
            'border': '#313244',
            'highlight': '#00d7ff',
            'success': '#a6e3a1',
            'danger': '#f38ba8',
            'warning': '#ffd700'
        }

    def main_loop(self):
        self.load_root()
        while self.running:
            self.render()
            input.check()

            if input.key("A"):
                self.handle_a()
            elif input.key("B"):
                self.handle_b()
            elif input.key("DY"):
                if input.value < 0:
                    self.handle_up()
                else:
                    self.handle_down()
            elif input.key("R1"):
                self.handle_r1()
            elif input.key("L1"):
                self.handle_l1()
            elif input.key("Y"):
                self.an.switch_sd_storage()
                app.current_sd = self.an.get_sd_storage()
                self.load_root()
            elif input.key("MENUF"):
                self.ui.draw_clear()
                self.ui.draw_text((self.screen_width // 2, self.screen_height // 2), self.lang.translate("Exiting..."), font=27, color=self.colors['text'], anchor="mm")
                self.ui.draw_paint()
                self.running = False
                print("[LocalUI] User pressed M, exit")
                break
            elif input.key("START"):
                self.handle_start()

            input.reset_input()
            time.sleep(0.05)

    def load_root(self, keep_index=False):
        self.show_loading_screen()
        self.current_path = ""
        self.current_items = get_subdirs(self.an.get_sd_storage())
        if keep_index:
            if self.selected_index >= len(self.current_items):
                self.selected_index = 0
        else:
            self.selected_index = self.dir_memory["root"]
            if self.selected_index >= len(self.current_items):
                self.selected_index = 0
                self.dir_memory["root"] = 0

        if self.selected_index >= self.max_display:
            self.scroll_offset = self.selected_index - self.max_display + 1
        else:
            self.scroll_offset = 0

        self.current_file = None
        self.mode = "browse"

    def load_directory(self, path, keep_index=False):
        self.show_loading_screen()
        app.current_sd = self.an.get_sd_storage()
        self.current_path = path
        self.current_items = get_files_in_dir(path, lang=self.lang.lang_code)
        if keep_index:
            if self.selected_index >= len(self.current_items):
                self.selected_index = 0
        else:
            self.selected_index = self.dir_memory["sub"].get(path, 0)
            if self.selected_index >= len(self.current_items):
                self.selected_index = 0
                self.dir_memory["sub"][path] = 0

        if self.selected_index >= self.max_display:
            self.scroll_offset = self.selected_index - self.max_display + 1
        else:
            self.scroll_offset = 0

        self.current_file = None
        self.mode = "browse"

    def get_selected_item(self):
        if not self.current_items or self.selected_index >= len(self.current_items):
            return None
        return self.current_items[self.selected_index]

    def handle_up(self):
        if self.mode == "browse":
            if not self.current_items:
                return
            if self.selected_index > 0:
                self.selected_index -= 1
            else:
                self.selected_index = len(self.current_items) - 1
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + self.max_display:
                self.scroll_offset = self.selected_index - self.max_display + 1
        elif self.mode == "menu":
            if not self.menu_options:
                return
            if self.menu_index > 0:
                self.menu_index -= 1
            else:
                self.menu_index = len(self.menu_options) - 1

    def handle_down(self):
        if self.mode == "browse":
            if not self.current_items:
                return
            if self.selected_index < len(self.current_items) - 1:
                self.selected_index += 1
            else:
                self.selected_index = 0
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + self.max_display:
                self.scroll_offset = self.selected_index - self.max_display + 1
        elif self.mode == "menu":
            if not self.menu_options:
                return
            if self.menu_index < len(self.menu_options) - 1:
                self.menu_index += 1
            else:
                self.menu_index = 0

    def handle_r1(self):
        if self.mode == "browse":
            self.selected_index = min(self.selected_index + self.max_display, len(self.current_items) - 1)
            if self.selected_index >= self.scroll_offset + self.max_display:
                self.scroll_offset = self.selected_index - self.max_display + 1
        elif self.mode == "menu":
            self.menu_index = min(self.menu_index + 3, len(self.menu_options) - 1)

    def handle_l1(self):
        if self.mode == "browse":
            self.selected_index = max(self.selected_index - self.max_display, 0)
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
        elif self.mode == "menu":
            self.menu_index = max(self.menu_index - 3, 0)

    def handle_a(self):
        if self.mode == "browse":
            item = self.get_selected_item()
            if not item:
                return
            if item.get('is_dir', False):
                    if self.current_path == "":
                        self.dir_memory["root"] = self.selected_index
                    else:
                        self.dir_memory["sub"][self.current_path] = self.selected_index
                    self.load_directory(item['path'])
            else:
                self.current_file = item
                self.mode = "detail"
                self.menu_index = 0
        elif self.mode == "detail":
            self.show_action_menu()
        elif self.mode == "menu":
            self.execute_menu_action()

    def handle_b(self):
        if self.mode == "menu":
            is_global_menu = (not self.current_file) or not any(action == "back" for _, action in self.menu_options)
            if is_global_menu:
                self.mode = "browse"
            else:
                self.mode = "detail"
        elif self.mode == "detail":
            self.mode = "browse"
            self.current_file = None
        elif self.mode == "browse":
            if self.current_path:
                parent = os.path.dirname(self.current_path)
                if parent:
                    self.dir_memory["sub"][self.current_path] = self.selected_index
                    self.load_directory(parent)
                else:
                    self.dir_memory["sub"][self.current_path] = self.selected_index
                    self.load_root()
            else:
                pass

    def handle_start(self):
        if self.mode == "browse":
            self.show_global_menu()

    def show_action_menu(self):
        if not self.current_file:
            return
        self.menu_options = [
            (self.lang.translate("Scrape preview"), "scrape"),
            (self.lang.translate("Delete game"), "delete"),
            (self.lang.translate("Delete preview"), "delete_preview"),
            (self.lang.translate("Back"), "back")
        ]
        self.menu_index = 0
        self.mode = "menu"

    def show_global_menu(self):
        self.menu_options = [
            (self.lang.translate("Batch scrape"), "batch_scrape"),
            (self.lang.translate("Go to root"), "root"),
            (self.lang.translate("Refresh"), "refresh"),
            (self.lang.translate("Exit"), "exit")
        ]
        self.menu_index = 0
        self.mode = "menu"

    def execute_menu_action(self):
        if self.menu_index >= len(self.menu_options):
            return
        action = self.menu_options[self.menu_index][1]

        if action == "scrape":
            self.do_scrape()
        elif action == "delete":
            self.do_delete()
        elif action == "delete_preview":
            self.do_delete_preview()
        elif action == "batch_scrape":
            self.do_batch_scrape()
        elif action == "root":
            self.load_root()
            self.mode = "browse"
        elif action == "refresh":
            if self.current_path:
                self.load_directory(self.current_path, keep_index=True)
            else:
                self.load_root(keep_index=True)
            self.mode = "browse"
        elif action == "exit":
            self.running = False
        elif action == "back":
            self.mode = "detail" if self.current_file else "browse"

    def do_scrape(self):
        if not self.current_file:
            return
        self.mode = "scraping"
        self.render_scraping(self.lang.translate("Scraping..."))

        try:
            result = self._scrape_single(self.current_file)
            if result:
                self.show_message(self.lang.translate("Scrape successful!"))
                file_path = self.current_file['path']
                if self.current_path:
                    self.load_directory(self.current_path)
                else:
                    self.load_root()
                if self._find_and_select_file(file_path):
                    self.current_file = self.current_items[self.selected_index]
                else:
                    self.current_file = None
                    self.mode = "browse"
                    return
            else:
                self.show_message(self.lang.translate("Scrape failed, please check network"))
        except Exception as e:
            self.show_message(self.lang.translate("Error: {error}").format(error=str(e)))

        if self.current_file:
            self.mode = "detail"
        else:
            self.mode = "browse"

    def _scrape_single(self, file_info):
        try:
            success, result = scrape_preview_for_path(file_info['path'])
            if success:
                self.current_file['preview'] = os.path.join(self.current_path, result)
                return True
            else:
                print(f"Scrape failed: {result}")
                return False
        except Exception as e:
            print(f"Scrape error: {e}")
            return False

    def do_delete(self):
        if not self.current_file:
            return
        if self.show_confirm(self.lang.translate("Delete {name} and its related files?").format(name=self.current_file['name'])):
            try:
                result = delete_game(self.current_file['path'])
                if result:
                    self.show_message(self.lang.translate("Delete successful"))
                    if self.current_path:
                        self.load_directory(self.current_path)
                    else:
                        self.load_root()
                else:
                    self.show_message(self.lang.translate("Delete failed"))
            except Exception as e:
                self.show_message(self.lang.translate("Error: {error}").format(error=str(e)))
        else:
            self.mode = "detail"
            return
        self.mode = "browse"

    def do_delete_preview(self):
        if not self.current_file:
            return
        if not self.current_file.get('preview'):
            self.show_message(self.lang.translate("This game has no preview"))
            self.mode = "detail"
            return
        if self.show_confirm(self.lang.translate('Delete preview image for "{name}"?').format(name=self.current_file['name'])):
            try:
                preview_path = self.current_file['preview']
                if os.path.exists(preview_path):
                    os.remove(preview_path)
                    self.show_message(self.lang.translate("Preview image deleted"))
                    file_path = self.current_file['path']
                    self.load_directory(self.current_path)
                    if self._find_and_select_file(file_path):
                        self.current_file = self.current_items[self.selected_index]
                    else:
                        self.current_file = None
                        self.mode = "browse"
                        return
                else:
                    self.show_message(self.lang.translate("Preview does not exist"))
            except Exception as e:
                self.show_message(self.lang.translate("Error: {error}").format(error=str(e)))
        else:
            self.mode = "detail"
            return

        if self.current_file:
            self.mode = "detail"
        else:
            self.mode = "browse"

    def do_batch_scrape(self):
        if not self.current_path:
            self.show_message(self.lang.translate("Please enter a game directory first"))
            return

        self.mode = "scraping"
        self.render_scraping(self.lang.translate("Batch scraping..."))

        try:
            items = get_files_in_dir(self.current_path, lang=self.lang.lang_code)
            to_scrape = [f for f in items if not f.get('is_dir', True) and not f.get('preview')]

            if not to_scrape:
                self.show_message(self.lang.translate("No games need scraping"))
                self.mode = "browse"
                return

            success = 0
            failed = 0

            for i, file_info in enumerate(to_scrape):
                self.render_scraping(
                    self.lang.translate("Scraping {current}/{total}: {name}").format(
                        current=i + 1,
                        total=len(to_scrape),
                        name=file_info['name']
                    )
                )

                ok, result = scrape_preview_for_path(file_info['path'])
                if ok:
                    success += 1
                else:
                    failed += 1
                    print(f"Scrape failed for {file_info['name']}: {result}")

                time.sleep(0.5)

            self.show_message(
                self.lang.translate("Batch scrape complete! Success: {success}, Failed: {failed}").format(
                    success=success, failed=failed
                )
            )
            self.load_directory(self.current_path)

        except Exception as e:
            self.show_message(self.lang.translate("Error: {error}").format(error=str(e)))

        self.mode = "browse"

    def _find_and_select_file(self, path):
        for i, item in enumerate(self.current_items):
            if item.get('path') == path:
                self.selected_index = i
                if i < self.scroll_offset:
                    self.scroll_offset = i
                if i >= self.scroll_offset + self.max_display:
                    self.scroll_offset = i - self.max_display + 1
                return True
        return False

    def show_loading_screen(self):
        ui = self.ui
        text = self.lang.translate("Loading...")
        ui.draw_rectangle_r([self.screen_width // 2 - 200, self.screen_height //2 - 50, self.screen_width // 2 + 200, self.screen_height // 2 + 50], radius=10, fill=self.colors['bg_list'])
        ui.draw_text((self.screen_width // 2, self.screen_height // 2), text, font=20, color=self.colors['text'], anchor="mm")
        ui.draw_paint()

    def show_message(self, text):
        self.mode = "message"
        self.render_message(text)
        time.sleep(3)
        self.mode = "browse"

    def show_confirm(self, text):
        self.mode = "confirm"
        self.render_confirm(text)
        while True:
            input.check()
            if input.key("A"):
                self.mode = "browse"
                return True
            elif input.key("B"):
                self.mode = "browse"
                return False
            input.reset_input()
            time.sleep(0.05)

    def render(self):
        if self.mode == "browse":
            self.render_browse()
        elif self.mode == "detail":
            self.render_detail()
        elif self.mode == "menu":
            self.render_menu()
        elif self.mode == "scraping":
            pass
        elif self.mode == "message":
            pass
        elif self.mode == "confirm":
            pass

    def render_browse(self):
        ui = self.ui
        ui.draw_clear()


        title = f"SD:{self.an.get_sd_storage()}"
        ui.draw_rectangle_r([0, 0, self.screen_width, 55], radius=0, fill=self.colors['bg_list'])
        ui.draw_text((10, 8), title, font=20, color=self.colors['text'])

        path_info = f"{self.lang.translate('Path')}: /Roms{'/' + self.current_path if self.current_path else ''}"
        ui.draw_text((10, 35), path_info, font=16, color=self.colors['text_secondary'])

        games_count = sum(1 for item in self.current_items if not item.get('is_dir', True))
        no_preview_count = sum(1 for item in self.current_items if not item.get('is_dir', True) and not item.get('preview'))
        count_text = f"{self.lang.translate('Total {count} items').format(count=len(self.current_items))} | {self.lang.translate('Games: ')}{games_count} | {self.lang.translate('Missing preview: ')}{no_preview_count}"
        ui.draw_text((self.screen_width - 10, 18), count_text, font=18,
                     color=self.colors['text_secondary'], anchor="rm")

        left_tip = self.lang.translate("Name")
        right_tip = self.lang.translate("Type | Size | P & G")
        ui.draw_text((20, 60), left_tip, font=18, color=self.colors['text_secondary'])
        ui.draw_text((self.screen_width - 10, 70), right_tip, font=18, color=self.colors['text_secondary'], anchor="rm")

        start_idx = self.scroll_offset
        end_idx = min(start_idx + self.max_display, len(self.current_items))

        for i in range(start_idx, end_idx):
            item = self.current_items[i]
            y = 85 + (i - start_idx) * 30
            is_selected = (i == self.selected_index)

            color = self.colors['item_selected'] if is_selected else self.colors['item_normal']
            ui.draw_rectangle_r([5, y, self.screen_width - 5, y + 28], radius=4, fill=color)

            icon = "▶ " if item.get('is_dir', False) else "♙ "
            name = item['name']
            if len(name) > 20:
                name = name[:20] + "..."
            ui.draw_text((15, y + 5), icon + name, font=19, color=self.colors['text'])

            if not item.get('is_dir', False):
                extension = os.path.splitext(item['path'])[1].lower()
                size = item.get('size', 0)
                size_str = f"{size/(1024):.0f}KB" if size < 1024*1024 else f"{size/(1024*1024):.1f}MB"
                preview_mark = "✔" if item.get('preview') else "✖"
                guide_mark = "✔" if item.get('guide_exists', False) else "✖"
                info = f"{extension} | {size_str} | {preview_mark}{guide_mark}"
                ui.draw_text((self.screen_width - 15, y + 15), info, font=19,
                             color=self.colors['text'], anchor="rm")
            else:
                game_count = item.get('game_count', 0)
                info = self.lang.translate("[ {count} games ]").format(count=game_count)
                ui.draw_text((self.screen_width - 15, y + 15), info, font=19,
                             color=self.colors['text_secondary'], anchor="rm")

        hint = self.lang.translate("Navigation: Up/Down, LR page, A confirm, B back, Y switch SD, Start menu, M exit")
        ui.draw_text((self.screen_width // 2, self.screen_height - 20), hint,
                     font=16, color=self.colors['text_dim'], anchor="mm")
        ui.draw_paint()

    def render_detail(self):
        if not self.current_file:
            self.mode = "browse"
            return
        ui = self.ui
        ui.draw_clear()
        file = self.current_file

        ui.draw_rectangle_r([0, 0, self.screen_width, 35], radius=0, fill=self.colors['bg_list'])
        name_display = os.path.basename(file.get('path', '')) if os.path.splitext(os.path.basename(file.get('path', '')))[0] == file['name'] else f"{os.path.basename(file.get('path', ''))} ({file['name']})"
        ui.draw_text((10, 8), f"☆ {name_display}", font=20, color=self.colors['text'])

        split_x = self.screen_width // 2
        left_margin = 15
        right_margin = 15

        right_x = split_x + 5
        right_width = self.screen_width - right_x - right_margin
        right_y = 45
        right_height = self.screen_height - 60 - 45

        left_x = left_margin
        y = 50
        lines = [
            (self.lang.translate("Platform: {platform}").format(platform=file.get('console', 'Unknown')), self.colors['text_secondary']),
            (self.lang.translate("Size: {size:.2f} MB").format(size=file.get('size', 0)/(1024*1024)), self.colors['text_secondary']),
            (self.lang.translate("Preview: {status}").format(
                status=self.lang.translate("Yes") if file.get('preview') else self.lang.translate("No")),
            self.colors['success'] if file.get('preview') else self.colors['danger']),
            (self.lang.translate("Guide: {status}").format(
                status=self.lang.translate("Yes") if file.get('guide_exists', False) else self.lang.translate("No")),
            self.colors['success'] if file.get('guide_exists', False) else self.colors['danger']),
            (self.lang.translate("Path: {path}").format(path=f"/Roms/{os.path.dirname(file.get('path', ''))}"), self.colors['text_dim'])
        ]
        for label, color in lines:
            ui.draw_text((left_x, y), label, font=18, color=color)
            y += 28

        ui.draw_rectangle_r([10, self.screen_height - 40, self.screen_width - 10, self.screen_height - 10],
                            radius=8, fill=self.colors['bg_list'])
        hint = self.lang.translate("A: Menu  B: Back")
        ui.draw_text((self.screen_width // 2, self.screen_height - 24), hint,
                    font=18, color=self.colors['text_dim'], anchor="mm")

        ui.draw_rectangle_r([right_x, right_y, right_x + right_width, right_y + right_height],
                        radius=8, fill='#2a2a3e', outline=self.colors['border'])

        preview_path = file.get('preview')
        if preview_path and os.path.exists(preview_path):
            try:
                from PIL import Image
                img = Image.open(preview_path)

                img_width, img_height = img.size
                target_width = right_width - 20
                target_height = right_height - 20
                scale = min(target_width / img_width, target_height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                img = img.resize((new_width, new_height), Image.LANCZOS)

                paste_x = right_x + (right_width - new_width) // 2
                paste_y = right_y + (right_height - new_height) // 2

                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                ui.active_image.paste(img, (paste_x, paste_y), img if img.mode == 'RGBA' else None)
            except Exception as e:
                print(f"Failed to load preview: {e}")
                ui.draw_text((right_x + right_width//2, right_y + right_height//2),
                            self.lang.translate("No preview"), font=20,
                            color=self.colors['text_secondary'], anchor="mm")
        else:
            ui.draw_text((right_x + right_width//2, right_y + right_height//2),
                        self.lang.translate("No preview"), font=20,
                        color=self.colors['text_secondary'], anchor="mm")

        ui.draw_paint()

    def render_menu(self):
        ui = self.ui
        ui.draw_clear()

        if self.current_file:
            file = self.current_file
            ui.draw_rectangle_r([0, 0, self.screen_width, 35], radius=0, fill=self.colors['bg_list'])
            name_display = os.path.basename(file.get('path', '')) if os.path.splitext(os.path.basename(file.get('path', '')))[0] == file['name'] else f"{os.path.basename(file.get('path', ''))} ({file['name']})"
            ui.draw_text((10, 8), f"☆ {name_display}", font=20, color=self.colors['text'])

            y = 50
            lines = [
                (self.lang.translate("Platform: {platform}").format(platform=file.get('console', 'Unknown')), self.colors['text_secondary']),
                (self.lang.translate("Size: {size:.2f} MB").format(size=file.get('size', 0)/(1024*1024)), self.colors['text_secondary']),
                (self.lang.translate("Preview: {status}").format(
                    status=self.lang.translate("Yes") if file.get('preview') else self.lang.translate("No")),
                 self.colors['success'] if file.get('preview') else self.colors['danger']),
                (self.lang.translate("Guide: {status}").format(
                    status=self.lang.translate("Yes") if file.get('guide_exists', False) else self.lang.translate("No")),
                 self.colors['success'] if file.get('guide_exists', False) else self.colors['danger']),
                (self.lang.translate("Path: {path}").format(path=f"/Roms/{os.path.dirname(file.get('path', ''))}"), self.colors['text_dim'])
            ]
            for label, color in lines:
                ui.draw_text((15, y), label, font=18, color=color)
                y += 28

            ui.draw_rectangle_r([10, self.screen_height - 40, self.screen_width - 10, self.screen_height - 10],
                                radius=8, fill=self.colors['bg_list'])
            hint = self.lang.translate("A: Menu  B: Back")
            ui.draw_text((self.screen_width // 2, self.screen_height - 24), hint,
                         font=18, color=self.colors['text_dim'], anchor="mm")

        ui.draw_rectangle_r([50, 100, self.screen_width - 50, self.screen_height - 100],
                            radius=12, fill='#1a1a2e', outline=self.colors['border'])
        ui.draw_text((self.screen_width // 2, 125), self.lang.translate("Operation menu"),
                     font=25, color=self.colors['text'], anchor="mm")

        for i, (label, action) in enumerate(self.menu_options):
            y = 150 + i * 32
            is_selected = (i == self.menu_index)
            color = self.colors['item_selected'] if is_selected else self.colors['item_normal']
            ui.draw_rectangle_r([70, y, self.screen_width - 70, y + 26], radius=4, fill=color)
            ui.draw_text((self.screen_width // 2, y + 13), label,
                         font=19, color=self.colors['text'], anchor="mm")

        ui.draw_paint()

    def render_scraping(self, text):
        ui = self.ui
        ui.draw_clear()
        ui.draw_rectangle_r([50, 100, self.screen_width - 50, self.screen_height - 100],
                            radius=12, fill='#1a1a2e', outline=self.colors['border'])
        ui.draw_text((self.screen_width // 2, self.screen_height // 2 - 10),
                     "㊣ " + text, font=24, color=self.colors['text'], anchor="mm")
        ui.draw_text((self.screen_width // 2, self.screen_height // 2 + 30),
                     self.lang.translate("Please wait..."), font=18, color=self.colors['text_secondary'], anchor="mm")
        ui.draw_paint()

    def render_message(self, text):
        ui = self.ui
        ui.draw_clear()
        ui.draw_rectangle_r([50, 120, self.screen_width - 50, self.screen_height - 120],
                            radius=12, fill='#1a1a2e', outline=self.colors['border'])
        ui.draw_text((self.screen_width // 2, self.screen_height // 2),
                    text, font=24, color=self.colors['text'], anchor="mm")

        ui.draw_paint()

    def render_confirm(self, text):
        ui = self.ui
        ui.draw_clear()
        ui.draw_rectangle_r([40, 120, self.screen_width - 40, self.screen_height - 120],
                            radius=12, fill='#1a1a2e', outline=self.colors['border'])
        ui.draw_text((self.screen_width // 2, self.screen_height // 2 - 60), "☢", font=40, color=self.colors['warning'], anchor="mm")
        lines = self._wrap_text(text, 30)
        y = self.screen_height // 2
        for line in lines:
            ui.draw_text((self.screen_width // 2, y), line, font=20, color=self.colors['text'], anchor="mm")
            y += 28
        ui.draw_text((self.screen_width // 2, y + 50),
                     self.lang.translate("A: Confirm  B: Cancel"),
                     font=18, color=self.colors['text_dim'], anchor="mm")
        ui.draw_paint()

    def _wrap_text(self, text, max_len):
        words = text.split()
        lines = []
        current = []
        for word in words:
            current.append(word)
            if len(' '.join(current)) > max_len:
                current.pop()
                lines.append(' '.join(current))
                current = [word]
        if current:
            lines.append(' '.join(current))
        return lines


def main():
    print("\n" + "="*50)
    print("  🎮 Anbernic 游戏管理器 - 本机端")
    print("="*50)
    print("  操作说明:")
    print("  ↑↓      - 选择项目")
    print("  A       - 确认 / 进入")
    print("  B       - 返回")
    print("  START   - 全局菜单")
    print("  SELECT  - 退出程序")
    print("="*50 + "\n")

    try:
        ui = LocalUI()
        ui.main_loop()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n本机端已退出")


if __name__ == "__main__":
    main()