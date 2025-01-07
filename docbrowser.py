from collections.abc import Callable
from enum import IntEnum
from inspect import Attribute
from sys import flags

from imgui import menu_item
from imgui.integrations.glfw import GlfwRenderer
import OpenGL.GL as gl
import glfw
import imgui
import sys
import subprocess

import logger
import config_file
import database
import tools
from database import BooKeeperDB
from processors.proc_arch import Arch_PROC
from processors.proc_base import BookInfo, BookFileType

config = config_file.BooKeeperConfig(sys.argv[1])
logger = logger.Logger(log_file=config.log_file_name, level=config.log_level)
db = database.BooKeeperDB(db_file_name=config.db_file_name, override_db = False)
def raise_(s):
    raise RuntimeError(s)
archive_processor = Arch_PROC(config.ram_drive_path,
                              config.language_option,
                              config.delete_artifacts,
                              lambda x,y : raise_('Invalid operation (on_scan_file)'),
                              lambda x,y : raise_('Invalid operation (on_book_callback)'),
                              lambda x,y,z : raise_('Invalid operation (on_archive_enter)'),
                              lambda : raise_('Invalid operation (on_archive_leave)'),
                              lambda x,y : raise_('Invalid operation (on_bad_callback)'),
                              BookFileType.ARCH_7Z)


class UserInterfaceMode (IntEnum):
    UI_SEARCH_MODE = 0
    UI_REPORT_MODE = 1

class UserInterfaceState:
    def __init__(self):
        self.message_box = None
        self.result_list_box = None
        self.search_bar = None
        self.mouse_x = -1
        self.mouse_y = -1
        self.main_window_width = -1
        self.main_window_height = -1
        self.ui_mode = UserInterfaceMode.UI_SEARCH_MODE
        self.report_text = """
This is report text, 
I don't know what to place here
Yet..."""

    def update(self):
        self.main_window_width, self.main_window_height = imgui.get_window_size()
        self.mouse_x, self.mouse_y = imgui.get_mouse_pos()

    def set_mode(self, mode: UserInterfaceMode):
        self.ui_mode = mode

ui = UserInterfaceState()

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

ui.message_box = MessageBox(ui)

class SearchBar:
    def __init__(self):
        self.last_query = ''

    def draw(self, on_query: Callable[[str], None]):
        res, query = imgui.input_text('', self.last_query, flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if res:
            self.last_query = query
            on_query(query)
        pass

ui.search_bar = SearchBar()

class ResultListBox:
    def __init__(self, database: BooKeeperDB):
        self.result_list = list()
        self.hash_list = list()
        self.result_list_pos = 0
        self.result_hovered_pos = 0
        self.db = database

    def draw(self):
        with imgui.begin_list_box("", -1, -1) as list_box:
            if list_box.opened:
                pos = 0
                for i in self.result_list:
                    opened, selected = imgui.selectable(i, pos == self.result_list_pos)
                    if selected:
                        self.result_list_pos = pos
                    if imgui.is_item_hovered():
                        self.result_hovered_pos = pos
                    pos += 1

    def do_search(self, query: str):
        res, self.result_list, self.hash_list = self.db.search_books(query)

    def get_active_item(self):
        if len(self.result_list):
            return True, self.result_list[self.result_list_pos], self.hash_list[self.result_list_pos]
        else:
            return False, '', ''

    def get_result_count(self):
        return len(self.result_list)
ui.result_list_box = ResultListBox(database=db)

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

ui.context_menu = ContextMenu(ui)

def set_style():
    style = imgui.get_style()
    imgui.style_colors_classic(style)

def on_open_book(ui: UserInterfaceState):
    res, file_name, hash = ui.result_list_box.get_active_item()
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

def on_report(ui: UserInterfaceState):
    res, file_name, hash = ui.result_list_box.get_active_item()
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

def draw_search_mode():
    global ui
    imgui.text('Search query:')
    imgui.same_line()

    imgui.push_item_width(-1)
    ui.search_bar.draw(lambda s: ui.result_list_box.do_search(s))
    ui.result_list_box.draw()
    imgui.pop_item_width()

    if imgui.is_mouse_released(1):
        ui.context_menu.show_context_menu()

    ui.context_menu.draw([
        ('Open', lambda: on_open_book(ui)),
        ('Report', lambda: on_report(ui))
    ])

    ui.message_box.draw()

def draw_report_mode():
    global ui
    if imgui.button('Close'):
        ui.set_mode(UserInterfaceMode.UI_SEARCH_MODE)

    res, file_name, hash = ui.result_list_box.get_active_item()
    text = f"""Number of results: {ui.result_list_box.get_result_count()}
{ui.report_text}
"""
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
def main():
    global app_font
    global window
    imgui.create_context()
    window = impl_glfw_init()
    impl = GlfwRenderer(window)

    io = imgui.get_io()
    app_font = io.fonts.add_font_from_file_ttf("./fonts/UbuntuMono-R.ttf",
                                               28.0,
                                               None,
                                               io.fonts.get_glyph_ranges_cyrillic())
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
    main()