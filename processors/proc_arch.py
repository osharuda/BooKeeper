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
from email.message import Message

from processors.proc_base import *
from tools import *
import re
import shutil

class Arch_PROC(Book_PROC):
    def __init__(self,
                 tmpdir: str,
                 lang_opt: str,
                 on_scan_file: Callable[[str, str], None],
                 on_book_callback: Callable[[str, BookInfo], None],
                 on_archive_enter: Callable[[str, str, str], None],
                 on_archive_leave: Callable[None, None],
                 on_bad_callback: Callable[[str, str], None],
                 arch_type: BookFileType):
        super().__init__(tmpdir, lang_opt, on_book_callback, on_bad_callback)
        self.arch_type = arch_type
        self.on_archive_enter = on_archive_enter
        self.on_archive_leave = on_archive_leave
        self.on_scan_file = on_scan_file
        self.uniq_counter = 0
        pass

    def unpack_archive(self, file_name: str, extract_path: str) -> str:
        match self.arch_type:
            case BookFileType.ARCH_7Z:
                self.unpack_7z(file_name, extract_path)
            case BookFileType.ARCH_RAR:
                self.unpack_rar(file_name, extract_path)
            case BookFileType.ARCH_ZIP:
                self.unpack_zip(file_name, extract_path)
            case BookFileType.ARCH_TARGZ:
                self.unpack_tar_gz(file_name, extract_path)
            case _:
                raise RuntimeError(f'Unsupported archive type: {self.arch_type}')

        return extract_path

    def make_tmp_dir(self):
        uniq_name = str(self.arch_type)+f'_{self.uniq_counter}'
        self.uniq_counter += 1
        tmp_dir = os.path.join(self.temp_dir, uniq_name)
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)
        return tmp_dir

    def unpack_tar_gz(self, file_name: str, target_dir: str):
        res, code, stdout = run_shell_adv(['tar', '-xzvf', file_name, '-C', target_dir], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {file_name}.\nError code: {code}\n{stdout}')

    def unpack_zip(self, file_name: str, target_dir: str):
        res, code, stdout = run_shell_adv(['unzip', file_name, f'-d', target_dir], print_stdout=False)
        self.add_write_perm_to_dir(target_dir)
        if code!=0 and code!=1:
            raise RuntimeError(f'Failed to extract an archive {file_name}.\nError code: {code}\n{stdout}')


    def unpack_rar(self, file_name: str, target_dir: str):
        res, code, stdout = run_shell_adv(['unrar', 'x', file_name, f'{target_dir}/'], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {file_name}.\nError code: {code}\n{stdout}')

    def unpack_7z(self, file_name: str, target_dir: str):
        res, code, stdout = run_shell_adv(['7z', 'x', file_name, f'-o{target_dir}'], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {file_name}.\nError code: {code}\n{stdout}')

    @staticmethod
    def add_write_perm_to_dir(path: str):
        res, code, stdout = run_shell_adv(['chmod', f'-R', f'+w', path], print_stdout=False)
        if not res:
            print(f'Failed set permissions for {path}.\nError code: {code}\n{stdout}')

    def process_file(self, file_name: str, file_hash: str):
        location_dir = os.path.dirname(file_name)
        base_name = os.path.basename(file_name)
        extract_path = self.make_tmp_dir()

        try:
            self.unpack_archive(file_name, extract_path)

            self.on_archive_enter(file_name, extract_path, file_hash)
            scan_directory(extract_path, on_file=self.on_scan_file, scan_param=(location_dir, base_name, extract_path))
            self.on_archive_leave()
        except RuntimeError as e:
            self.on_bad_callback(file_name, str(e))

        shutil.rmtree(extract_path)

    def get_page_with_ocr(self, file_name: str, page: int, page_num: int) -> str:
        raise RuntimeError(f'get_page_with_ocr() is not implemented for {type(self)}')

    def get_page_text_layer(self, file_name: str, page: int, page_num: int) -> str:
        raise RuntimeError(f'get_page_text_layer() is not implemented for {type(self)}')
