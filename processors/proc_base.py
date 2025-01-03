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

import threading
from collections.abc import Callable
from enum import IntEnum
from abc import ABC, abstractmethod
from tools import *
import os
from threading import *

class BookFileType(IntEnum):
    NONE = 0
    DJVU = 1
    PDF = 2
    DOC = 3
    RTF = 4
    TXT = 5
    FB2 = 6
    ARCH_TARGZ = 7
    ARCH_RAR = 8
    ARCH_ZIP = 9
    ARCH_7Z = 10

book_archive_types = {BookFileType.ARCH_TARGZ, BookFileType.ARCH_7Z, BookFileType.ARCH_ZIP, BookFileType.ARCH_RAR}

class BookInfo:
    def __init__(self):
        self.book_type = BookFileType.NONE
        self.name = ""
        self.ocr = False
        self.page_count = -1
        self.size = -1
        self.text_data = ""
        self.hash_value = ""

class Book_PROC(ABC):
    def __init__(self,
                 tmpdir: str,
                 lang_opt: str,
                 on_book_callback: Callable[[str, BookInfo], None],
                 on_bad_callback: Callable[[str, str], None]):
        self.temp_dir = tmpdir
        self.lang_opt = lang_opt
        self.on_book_callback = on_book_callback
        self.max_page = 4
        self.max_text_data_len = 1024
        self.on_bad_callback = on_bad_callback
        pass

    @abstractmethod
    def process_file(self, file_name: str, file_hash: str):
        pass

    @abstractmethod
    def get_page_with_ocr(self, file_name: str, page: int, page_num: int) -> str:
        pass

    @abstractmethod
    def get_page_text_layer(self, file_name: str, page: int, page_num: int) -> str:
        pass

    def extract_text(self, file_name: str, max_page: int) -> tuple[str, bool]:
        raw_text = ''
        ocr = False
        for i in range(0, self.max_page):
            t, page_ocr = self.get_page_text(file_name, i, max_page)
            ocr = ocr or page_ocr
            raw_text = raw_text + ' ' + t

        raw_text = self.raw_text_filter(raw_text)
        if len(raw_text) > self.max_text_data_len:
            raw_text = raw_text[:self.max_text_data_len]
            index = raw_text.rfind(' ')
            if index >= 0:
                raw_text = raw_text[:index]

        return raw_text, ocr

    def get_page_text(self, file_name: str, page: int, page_num) -> tuple[str, bool]:
        if page >= page_num:
            return '', False

        s = self.get_page_text_layer(file_name, page, page_num)
        ocr = False
        if len(s.strip()) == 0:
            s = self.get_page_with_ocr(file_name, page, page_num)
            ocr = True

        return s, ocr


    def process_book_name(self, file_name: str):
        return file_name


    def normalize_path(self, library_path: str):
        pass

    @staticmethod
    def tokenize_text(t: str) -> set[str]:
        sep = ' '
        t = t.lower()
        trans = str.maketrans({'\n': sep, '\r': sep, '\t': sep, '\\': sep, '_': sep, '"': sep, "'": sep, })
        t = t.translate(trans)
        wl = t.split(sep)
        wl = list(filter(lambda emp: len(emp) > 0, wl))

        res = set()
        for w in wl:
            res.add(w)

        return res

    @staticmethod
    def raw_text_filter(t: str) -> str:
        sep = ' '
        trans = str.maketrans({ '\n': sep, '\r': sep, '\t': sep, '\\': sep, '_': sep, '"': sep, "'": sep, '!': sep,
                                '#': sep, '$': sep, '%': sep, '&': sep, '(': sep, ')': sep, '*': sep, '+': sep, ',': sep,
                                '-': sep, '/': sep, ':': sep, ';': sep, '<': sep, '=': sep,	'>': sep, '?': sep, '[': sep,
                                ']': sep, '^': sep, '`': sep, '{': sep, '|': sep, '}': sep, '~': sep })
        t = t.translate(trans)
        wl = t.split(sep)
        wl = list(filter(lambda emp: len(emp) > 0, wl))

        return sep.join(wl)

    def ocr_text(self, image_file_name: str) -> str:
        uniq_name = str(threading.current_thread().native_id)
        base_name = os.path.join(self.temp_dir, f'{uniq_name}')
        png_name = f'{base_name}.png'
        txt_name = f'{base_name}.txt'
        res, code, stdout = run_shell_adv(['convert',
                                           f'{image_file_name}',
                                            '-enhance',
                                            '-enhance',
                                            '-enhance',
                                            '-enhance',
                                            '-enhance',
                                            '-enhance',
                                            '-enhance',
                                            f'{png_name}'],
                                          print_stdout=False)
        if res is False:
            raise RuntimeError(f'Failed to convert page image to png. convert returned error: {code}\n{stdout}')

        res, code, stdout = run_shell_adv(['tesseract',
                                           f'{png_name}',
                                           f'{base_name}',
                                           '-l',
                                           self.lang_opt],
                                          print_stdout=False)
        if res is False:
            raise RuntimeError(f'Failed to recognize text: {code}\n{stdout}')

        res = read_text_file(txt_name)

        os.unlink(png_name)
        os.unlink(txt_name)

        return res


book_extensions = { # BookFileType.DOC : {'.doc', '.docx', '.odt'},
                    # BookFileType.RTF : {'.rtf'},
                    # BookFileType.TXT : {'.txt'},
                    # BookFileType.FB2 : {'.fb2'}
                    BookFileType.ARCH_TARGZ : {'.tar.gz'},
                    BookFileType.ARCH_RAR : {'.rar', '.RAR', 'Rar'},
                    BookFileType.ARCH_ZIP : {'.zip', '.ZIP', '.Zip'},
                    BookFileType.ARCH_7Z : {'.7z', '.7Z'},
                    BookFileType.DJVU : {'.djvu', '.djv'},
                    BookFileType.PDF : {'.pdf'}}

all_book_extensions = set()
for k, e in book_extensions.items():
    all_book_extensions = all_book_extensions.union(e)

def get_book_type(file_name: str) -> BookFileType:
    """ Returns book type from file name

    Note:
        File content may be read.

    Args:
        file_name (str) : Book file name.

    Returns:
        BookFileType: Type of the book
    """

    root, ext = split_file_name(file_name, all_book_extensions)
    ext = ext.lower()

    for bt, bext in book_extensions.items():
        if ext in bext and bt in book_extensions.keys():
            return bt
    return BookFileType.NONE