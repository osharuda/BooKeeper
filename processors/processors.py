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

from processors.proc_arch import *
from processors.proc_base import *
from processors.proc_djvu import *
from processors.proc_pdf import *


def init_processors(temp_dir: str,
                    lang_opt: str,
                    on_scan_file: Callable[[str, str], None],
                    on_book_callback: Callable[[str, BookInfo], None],
                    on_archive_enter: Callable[[str, str, str], None],
                    on_archive_leave: Callable[None, None],
                    on_bad_book_callback: Callable[[str, str], None],
                    on_bad_archive_callback: Callable[[str, str], None]):
    processor_map = dict()
    processor_map[BookFileType.DJVU] = Djvu_PROC(temp_dir, lang_opt, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.PDF] = Pdf_PROC(temp_dir, lang_opt, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.ARCH_TARGZ] = Arch_PROC(temp_dir, lang_opt, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_TARGZ)
    processor_map[BookFileType.ARCH_RAR] = Arch_PROC(temp_dir, lang_opt, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_RAR)
    processor_map[BookFileType.ARCH_ZIP] = Arch_PROC(temp_dir, lang_opt, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_ZIP)
    processor_map[BookFileType.ARCH_7Z] = Arch_PROC(temp_dir, lang_opt, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_7Z)
    return processor_map
