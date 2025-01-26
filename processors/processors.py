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

from processors.proc_arch import *
from processors.proc_djvu import *
from processors.proc_doc import *
from processors.proc_docx import *
from processors.proc_fb2 import *
from processors.proc_odt import *
from processors.proc_pdf import *
from processors.proc_rtf import *


def init_processors(temp_dir: str,
                    lang_opt: str,
                    delete_artifacts: bool,
                    on_scan_file: Callable[[str, str], None],
                    on_book_callback: Callable[[str, BookInfo], None],
                    on_archive_enter: Callable[[str, str, str], None],
                    on_archive_leave: Callable[None, None],
                    on_bad_book_callback: Callable[[str, str], None],
                    on_bad_archive_callback: Callable[[str, str], None]):
    """
    Initializes file processors
    Args:
        temp_dir: Temporary directory to extract files (RAM drive)
        lang_opt: Language option
        delete_artifacts: If true all temporary and intermediate files will be deleted. For debug purposes set false.
        on_scan_file: Callback to be called for every file.
        on_book_callback: Callback to be called for every discovered book.
        on_archive_enter: Callback to be called when entering into some archive.
        on_archive_leave: Callback to be called when leave into some archive.
        on_bad_book_callback: Callback to be called for every broken book.
        on_bad_archive_callback: Callback to be called for every broken archive.

    Returns: dict() with all processors (key is BookFileType)

    """
    processor_map = dict()
    processor_map[BookFileType.DJVU] = Djvu_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.PDF] = Pdf_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.FB2] = Fb2_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.DOCX] = Docx_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.DOC] = Doc_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.ODT] = Odt_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.RTF] = Rtf_PROC(temp_dir, lang_opt, delete_artifacts, on_book_callback, on_bad_book_callback)
    processor_map[BookFileType.ARCH_TARGZ] = Arch_PROC(temp_dir, lang_opt, delete_artifacts, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_TARGZ)
    processor_map[BookFileType.ARCH_RAR] = Arch_PROC(temp_dir, lang_opt, delete_artifacts, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_RAR)
    processor_map[BookFileType.ARCH_ZIP] = Arch_PROC(temp_dir, lang_opt, delete_artifacts, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_ZIP)
    processor_map[BookFileType.ARCH_7Z] = Arch_PROC(temp_dir, lang_opt, delete_artifacts, on_scan_file, on_book_callback, on_archive_enter, on_archive_leave, on_bad_archive_callback, BookFileType.ARCH_7Z)
    return processor_map
