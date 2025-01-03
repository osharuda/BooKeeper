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

from processors.proc_base import *
from tools import *
import shutil
import re


class Pdf_PROC(Book_PROC):
    def __init__(self,
                 tmpdir: str,
                 lang_opt: str,
                 on_book_callback: Callable[[str, BookInfo], None],
                 on_bad_callback: Callable[[str, str], None]):
        super().__init__(tmpdir, lang_opt, on_book_callback, on_bad_callback)
        self.page_num_re = re.compile(r'^Pages:\s+(\d+)\s*$', re.MULTILINE)
        pass

    def process_file(self, file_name: str, file_hash: str):
        info = BookInfo()
        info.book_type = BookFileType.PDF
        info.name = self.process_book_name(file_name)
        info.size = os.path.getsize(file_name)
        info.hash_value = file_hash

        res, code, stdout = run_shell_adv(['pdfinfo', file_name],
                                          print_stdout=False)
        if res is False:
            raise RuntimeError(f"Failed to get pdf information: {code}\n{stdout}")

        m = re.search(self.page_num_re, stdout)
        if not m:
            raise RuntimeError(f"Failed to get pdf file page count.")

        info.page_count = int(m.group(1))

        (info.text_data, info.ocr) = self.extract_text(file_name, info.page_count)
        self.on_book_callback(file_name, info)


    def get_page_with_ocr(self, file_name: str, page: int, page_num: int) -> str:
        page += 1
        base_name = os.path.join(self.temp_dir, f'{os.path.basename(file_name)}')
        base_name = os.path.join(self.temp_dir, f'image')

        # pdftoppm produces page number as 000xxx, where xxx - is actual page number with heading zeroes,
        # so the total string length is the same as length of the page_num
        pnl = len(str(page_num))
        pl = len(str(page))
        page_str = '0'*(pnl - pl) + str(page)

        ppm_name = f'{base_name}-{page_str}.ppm'
        res, code, stdout = run_shell_adv(['pdftoppm', file_name, f'-f', f'{page}', f'-l', f'{page}', base_name],
                                          print_stdout=False)
        if res is False:
            if os.path.isfile(ppm_name):
                os.unlink(ppm_name)
            raise RuntimeError(f'Failed to extract page image. pdftoppm returned error: {code}\n{stdout}')

        res = self.ocr_text(ppm_name)
        os.unlink(ppm_name)
        return res

    def get_page_text_layer(self, file_name: str, page: int, page_num: int) -> str:
        page += 1
        out_name = os.path.join(self.temp_dir, f'{os.path.basename(file_name)}.{page}.txt')
        res, code, stdout = run_shell_adv(['pdftotext', file_name, f'-f', f'{page}', f'-l', f'{page}', out_name],
                                          print_stdout=False)
        if res is False:
            if os.path.isfile(out_name):
                os.unlink(out_name)
            raise RuntimeError(f'Failed to extract text layer. pdftotext returned error: {code}\n{stdout}')

        res = read_text_file(out_name).strip()
        os.unlink(out_name)

        return res
