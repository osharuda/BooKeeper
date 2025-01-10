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
from processors.proc_base import *


class Doc_PROC(Book_PROC):
    def __init__(self,
                 tmpdir: str,
                 lang_opt: str,
                 delete_artifacts: bool,
                 on_book_callback: Callable[[str, BookInfo], None],
                 on_bad_callback: Callable[[str, str], None]):
        super().__init__(tmpdir, lang_opt, delete_artifacts, on_book_callback, on_bad_callback)
        pass

    def process_file(self, file_name: str, file_hash: str):
        info = BookInfo()
        info.book_type = BookFileType.DOCX
        info.name = self.process_book_name(file_name)
        info.size = os.path.getsize(file_name)
        info.hash_value = file_hash
        info.page_count = -1
        info.text_data, info.ocr = self.extract_text(file_name, info.page_count)
        self.on_book_callback(file_name, info)


    def get_page_with_ocr(self, file_name: str, page: int, page_num: int) -> str:
        raise RuntimeError('Not implemented')


    def get_page_text_layer(self, file_name: str, page: int, page_num: int) -> str:
        return self.get_pandoc_text(file_name, 'docx')
