"""
    Copyright 2025 Oleh Sharuda <oleh.sharuda@gmail.com>


    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
 """
import os.path
import shutil
from collections.abc import Callable
from enum import IntEnum
from imgui.integrations.glfw import GlfwRenderer
import OpenGL.GL as gl
import glfw
import imgui
import sys
import subprocess

import logger
from config_file import BooKeeperConfig
import database
import tools
from database import BooKeeperDB
from processors.proc_arch import Arch_PROC
from processors.proc_base import BookInfo, BookFileType


def raise_(s):
    raise RuntimeError(s)


class UserInterfaceMode (IntEnum):
    UI_SEARCH_MODE = 0
    UI_REPORT_MODE = 1

class UserInterfaceState:
    def __init__(self, config: BooKeeperConfig):
        self.message_box = None
        self.result_list_box = None
        self.search_bar_list = list()
        self.mouse_x = -1
        self.mouse_y = -1
        self.main_window_width = -1
        self.main_window_height = -1
        self.ui_mode = UserInterfaceMode.UI_SEARCH_MODE
        self.report_text = ''
        self.config = config

    def update(self):
        self.main_window_width, self.main_window_height = imgui.get_window_size()
        self.mouse_x, self.mouse_y = imgui.get_mouse_pos()

    def set_mode(self, mode: UserInterfaceMode):
        self.ui_mode = mode


class MessageBox:
    def __init__(self, state: UserInterfaceState):
        self.message_box_title = ''
        self.message_box_text = ''
        self.state = state

    def show_message_box(self, msg: str, title: str):
        self.message_box_title = title
        self.message_box_text = msg

    def close_message_box(self):
        self.message_box_title = ''
        self.message_box_text = ''

    def draw(self):
        if len(self.message_box_title) == 0:
            return
        imgui.open_popup(self.message_box_title)
        width = max(imgui.calc_text_size(self.message_box_title)[0], imgui.calc_text_size(self.message_box_text)[0])
        width = width * 1.2
        imgui.set_next_window_size(width, 0.0)
        opened, visible = imgui.begin_popup_modal(self.message_box_title, True)
        if opened:
            imgui.text(self.message_box_text)
            if imgui.button('OK'):
                self.close_message_box()
            imgui.end_popup()
        else:
            self.close_message_box()

class SearchBar:
    def __init__(self):
        self.last_query = ''
        self.max_search_bars = 7

    def update_text(self, cbdata):
        if cbdata.event_flag != imgui.INPUT_TEXT_CALLBACK_ALWAYS:
            return
        self.last_query = cbdata.buffer

    def draw(self, n: int,
                   on_query: Callable[[None], None],
                   on_remove: Callable[[int], None],
                   on_add: Callable[[int], None]):
        imgui.text('Search:')
        imgui.same_line()

        imgui.push_item_width(-80)
        imgui.push_id(f'search_edit_{n}')
        res, query = imgui.input_text('',
                                      self.last_query,
                                      callback=self.update_text,
                                      flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE |
                                      imgui.INPUT_TEXT_CALLBACK_ALWAYS)
        imgui.pop_id()
        imgui.pop_item_width()

        if res:
            on_query()

        if n + 1 < self.max_search_bars:
            imgui.same_line()
            imgui.push_id(f'plus_btn_{n}')
            if imgui.button('+'):
                on_add(n)
            imgui.pop_id()

        imgui.same_line()
        imgui.push_id(f'minus_btn_{n}')
        if imgui.button('-'):
            on_remove(n)
        imgui.pop_id()

class ResultListBox:
    def __init__(self, database: BooKeeperDB):
        self.result_list = list()
        self.hash_list = list()
        self.text_data_list = list()
        self.search_spans_list = list()
        self.result_hovered_pos = 0
        self.last_clicked_pos = 0
        self.db = database
        self.normal_color = (1.0, 0.7, 0.7, 1.0)
        self.normal_color_2 = (1.0, 1.0, 0.6, 1.0)
        self.text_data = ''
        self.span_data = list()
        self.span_data_index = -1
        self.max_text_data = " x" * 1024

    def draw(self):

        if self.text_data:
            selected_text = tools.select_text(self.text_data, self.span_data[self.span_data_index])
            text_dims = imgui.calc_text_size(selected_text)
            wrapped_text = tools.wrap_text(selected_text, text_dims.x, imgui.get_window_width())
            imgui.input_text_multiline('text_data', wrapped_text)
            if imgui.button('<'):
                self.span_data_index -= 1

            imgui.same_line()
            if imgui.button('>'):
                self.span_data_index += 1

            if self.span_data_index < 0:
                self.span_data_index = 0

            if self.span_data_index >= len(self.span_data):
                self.span_data_index = len(self.span_data) - 1

        with imgui.begin_list_box("", -1, -1) as list_box:
            if list_box.opened:
                pos = 0
                last_hash=''
                mark_type = True
                normal_color = imgui.get_style_color_vec_4(imgui.COLOR_TEXT)
                for i in self.result_list:
                    hash = self.hash_list[pos]
                    if hash != last_hash:
                        last_hash = hash
                        mark_type = not mark_type

                    if mark_type:
                        imgui.push_style_color(imgui.COLOR_TEXT, *self.normal_color)
                    else:
                        imgui.push_style_color(imgui.COLOR_TEXT, *self.normal_color_2)

                    imgui.selectable(i, pos == self.last_clicked_pos)
                    if imgui.is_item_hovered():
                        self.result_hovered_pos = pos

                    if imgui.is_item_clicked():
                        self.text_data = self.text_data_list[pos]
                        self.span_data = self.search_spans_list[pos]
                        self.span_data_index = 0
                        self.last_clicked_pos = pos

                    imgui.pop_style_color()

                    pos += 1


    def do_search(self, queries: list[str]):
        self.text_data = ''
        res, self.result_list, self.hash_list, self.text_data_list, self.search_spans_list = self.db.search_books_in_cache(queries)
        pass

    def get_active_item(self):
        if len(self.result_list):
            return True, self.result_list[self.result_hovered_pos], self.hash_list[self.result_hovered_pos], self.text_data_list[self.result_hovered_pos]
        else:
            return False, '', '', ''

    def get_result_count(self):
        return len(self.result_list)

class ContextMenu:
    def __init__(self, state: UserInterfaceState):
        self.state = state
        self.context_menu_width = 150
        self.context_menu_x = -1
        self.context_menu_y = -1
        self.context_menu_opened = False
        self.hovered_item = -1

    def show_context_menu(self):
        imgui.open_popup_on_item_click('context menu')

    def is_opened(self):
        return self.context_menu_opened

    def draw(self,
             items: list[ tuple[str, Callable[[], None]]]):
        self.context_menu_opened, visible = imgui.begin_popup_modal(
            'context menu',
            flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE)

        style = imgui.get_style()
        ctx_height = (imgui.get_text_line_height_with_spacing() * len(items) +
                      2 * (style.window_padding.y + style.frame_padding.y))

        if not self.context_menu_opened:
            self.context_menu_x = self.state.mouse_x
            self.context_menu_y = self.state.mouse_y

            if self.context_menu_x + self.context_menu_width > self.state.main_window_width:
                self.context_menu_x = self.state.main_window_width - self.context_menu_width

            if self.context_menu_y + ctx_height > self.state.main_window_height:
                self.context_menu_y = self.state.main_window_height - ctx_height
        else:
            imgui.set_window_size(self.context_menu_width, ctx_height)
            imgui.set_window_position(self.context_menu_x, self.context_menu_y)

            imgui.push_item_width(-1)
            with imgui.begin_list_box("", -1, -1) as ctx_menu_list:
                if ctx_menu_list.opened:
                    pos = 0
                    self.hovered_item = -1
                    for i, cb in items:
                        opened, selected = imgui.selectable(i, False)
                        if imgui.is_item_hovered():
                            self.hovered_item = pos
                        if imgui.is_item_clicked(0):
                            cb()
                        pos += 1

            imgui.pop_item_width()

            if ((imgui.is_mouse_released(0)) and
                    not imgui.is_window_hovered(imgui.HOVERED_ALLOW_WHEN_BLOCKED_BY_POPUP)):
                imgui.close_current_popup()

            imgui.end_popup()


def set_style():
    style = imgui.get_style()
    imgui.style_colors_classic(style)

def on_open_book(ui: UserInterfaceState):
    res, file_name, hash, text_data = ui.result_list_box.get_active_item()
    if not res:
        return
    try:
        extracted_file = archive_processor.unpack_file(file_name)
        subprocess.run(['open', extracted_file])
    except Exception as e:
        ui.report_text = f"""Failed to process file:
{file_name}

Exception:
{str(e)}
"""
        ui.set_mode(UserInterfaceMode.UI_REPORT_MODE)

    return

def on_export_book(ui: UserInterfaceState):
    res, file_name, hash, text_data = ui.result_list_box.get_active_item()
    if not res:
        return
    try:
        extracted_file = archive_processor.unpack_file(file_name)
        shutil.move(extracted_file, ui.config.export_path)
    except Exception as e:
        ui.report_text = f"""Failed to process file:
{file_name}

Exception:
{str(e)}
"""
        ui.set_mode(UserInterfaceMode.UI_REPORT_MODE)

    return

def on_report(ui: UserInterfaceState):
    res, file_name, hash, text_data = ui.result_list_box.get_active_item()
    if not res:
        return

    res = db.get_book_info(hash)
    if res:
        size, ocr, booktype, page_count, text_data, tokens = res
        bi = BookInfo(book_type = booktype,
                     name = file_name,
                     ocr = ocr,
                     page_count = page_count,
                     size = size,
                     text_data = text_data,
                     hash_value = hash)
        ui.report_text = tools.wrap_text(bi.to_report(), 150)
        ui.set_mode(UserInterfaceMode.UI_REPORT_MODE)

def on_enter():
    global ui
    queries = list()
    for sb in ui.search_bar_list:
        if sb.last_query:
            queries.append(sb.last_query)

    if queries:
        ui.result_list_box.do_search(queries)

def add_search(n: int):
    global ui
    if len(ui.search_bar_list) < ui.search_bar_list[n].max_search_bars:
        ui.search_bar_list.insert(n + 1, SearchBar())

def remove_search(n: int):
    if len(ui.search_bar_list) > 1:
        ui.search_bar_list.pop(n)


def draw_search_mode():
    global ui
    global ram_drive_warning
    global bad_lib_paths
    global export_path_warning

    n = 0
    for sb in ui.search_bar_list:
        sb.draw(n, on_enter, remove_search, add_search)
        n += 1

    imgui.push_item_width(-1)
    if ui.result_list_box.get_result_count():
        ui.result_list_box.draw()
    imgui.pop_item_width()

    if imgui.is_mouse_released(1):
        ui.context_menu.show_context_menu()

    ui.context_menu.draw([
        ('Open', lambda: on_open_book(ui)),
        ('Export', lambda: on_export_book(ui)),
        ('Report', lambda: on_report(ui))
    ])

    if ram_drive_warning:
        ui.message_box.show_message_box("Warning: RAM drive is not mounted.\nArchived books will fail to open.", "Warning")
        ram_drive_warning = False

    if len(export_path_warning):
        warn_text = "Warning: Export path is not accessible.\nExport function will not work.\n" + export_path_warning
        ui.message_box.show_message_box(warn_text, "Warning")
        export_path_warning = ''

    if bad_lib_paths:
        warn_text = "Warning: Some libraries are not accessible:\n" + "\n".join(bad_lib_paths)
        ui.message_box.show_message_box(warn_text, "Warning")
        bad_lib_paths.clear()

    ui.message_box.draw()

def draw_report_mode():
    global ui
    if imgui.button('Close'):
        ui.set_mode(UserInterfaceMode.UI_SEARCH_MODE)

    res, file_name, hash, text_data = ui.result_list_box.get_active_item()
    text = f"""{ui.report_text}"""
    imgui.input_text_multiline('report', text, width=-1, height=-1, flags=imgui.INPUT_TEXT_READ_ONLY)

def gui():
    global ui
    global app_font
    global window

    win_w, win_h = glfw.get_window_size(window)
    imgui.set_next_window_position(0.0, 0.0)
    imgui.set_next_window_size(win_w, win_h)


    imgui.begin("ui", False, imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE)
    ui.update()
    imgui.push_font(app_font)

    match ui.ui_mode:
        case UserInterfaceMode.UI_SEARCH_MODE:
            draw_search_mode()
        case UserInterfaceMode.UI_REPORT_MODE:
            draw_report_mode()

    imgui.pop_font()
    imgui.end()


app_font = None
window = None
ram_drive_warning = True
export_path_warning = ''
bad_lib_paths = []
def main():
    global app_font
    global window
    global ram_drive_warning
    global bad_lib_paths
    global export_path_warning
    ram_drive_warning = not tools.is_ramdrive_mounted(config.ram_drive_path)
    bad_lib_paths = tools.check_paths(config.libraries)
    export_path_warning = '' if os.path.isdir(config.export_path) else config.export_path
    imgui.create_context()
    window = impl_glfw_init()
    impl = GlfwRenderer(window)

    io = imgui.get_io()
    io.add_input_characters_utf8("⭆")
    #g = io.fonts.get_glyph_ranges_cyrillic()
    g = imgui.core.GlyphRanges([0x0020, 0x007F, 0x0400, 0x04FF, 0x02500, 0x025FF, 0])


    app_font = io.fonts.add_font_from_file_ttf("./fonts/UbuntuMono-R.ttf",
                                               28.0,
                                               None,
                                               g)

    impl.refresh_font_texture()
    set_style()

    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()

        imgui.new_frame()

        gui()

        gl.glClearColor(1.0, 1.0, 1.0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    impl.shutdown()
    glfw.terminate()


def impl_glfw_init():
    width, height = 1280, 720
    window_name = "BooKeeper Browser"

    if not glfw.init():
        print("Could not initialize OpenGL context")
        sys.exit(1)

    # OS X supports only forward-compatible core profiles from 3.2
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

    # Create a windowed mode window and its OpenGL context
    window = glfw.create_window(int(width), int(height), window_name, None, None)
    glfw.make_context_current(window)

    if not window:
        glfw.terminate()
        print("Could not initialize Window")
        sys.exit(1)

    return window

if __name__ == "__main__":
    config = BooKeeperConfig(sys.argv[1])
    logger = logger.Logger(log_file=config.log_file_name, level=config.log_level)
    db = database.BooKeeperDB(db_file_name=config.db_file_name,
                              ram_drive_db=False,
                              override_db=False)

    ui = UserInterfaceState(config)
    ui.message_box = MessageBox(ui)
    ui.search_bar_list.append(SearchBar())
    ui.result_list_box = ResultListBox(database=db)
    ui.context_menu = ContextMenu(ui)

    archive_processor = Arch_PROC(config.ram_drive_path,
                                  config.language_option,
                                  config.delete_artifacts,
                                  lambda x, y: raise_('Invalid operation (on_scan_file)'),
                                  lambda x, y: raise_('Invalid operation (on_book_callback)'),
                                  lambda x, y, z: raise_('Invalid operation (on_archive_enter)'),
                                  lambda: raise_('Invalid operation (on_archive_leave)'),
                                  lambda x, y: raise_('Invalid operation (on_bad_callback)'),
                                  BookFileType.ARCH_7Z)

    main()

    db.finalize()