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

import os
import shutil

from database import BooKeeperDB
from docbrowser import logger
from processors.proc_base import get_book_type, BookInfo, BookFileType, book_archive_types
from processors.processors import init_processors
from terminator import Terminator
from tools import get_file_hash, test_unicode_string, scan_directory
from logger import Logger


class Scanner:
    def __init__(self,
                 library_path: str,
                 ram_drive_path:str,
                 language_option: str,
                 delete_artifacts: bool):
        self.archive_stack = list()
        self.current_logical_path = ''
        self.db = BooKeeperDB()
        self.logger = Logger()
        self.terminator = None
        self.ram_drive_path = ram_drive_path
        self.language_option = language_option
        self.library_path = library_path
        self.delete_artifacts = delete_artifacts
        self.processor_map = init_processors(
            temp_dir=self.ram_drive_path,
            lang_opt=self.language_option,
            delete_artifacts=self.delete_artifacts,
            on_scan_file=self.on_scan_file,
            on_book_callback=self.on_book,
            on_archive_enter=self.on_archive_enter,
            on_archive_leave=self.on_archive_leave,
            on_bad_book_callback=self.on_bad_book,
            on_bad_archive_callback=self.on_bad_archive)
        pass

    def scan(self):
        self.terminator = Terminator()
        scan_directory(self.library_path, on_file=self.on_scan_file)


    def update_logical_path(self):
        self.current_logical_path = ''
        if len(self.archive_stack) == 0:
            return
        else:
            tmp = '/'
            self.current_logical_path = '/'
            for (afn, ep, h) in self.archive_stack:
                rel_path = os.path.relpath(afn, tmp)
                self.current_logical_path = os.path.join(self.current_logical_path, rel_path)
                tmp = ep

    def get_parent_archive_hash(self) -> str:
        parent_arch_hash = ''
        if len(self.archive_stack):
            parent_arch_hash = self.archive_stack[-1][2]

        return parent_arch_hash

    def on_archive_enter(self, arch_file_name: str, extract_path: str, file_hash: str):
        arch_logical_name = self.get_logical_name(arch_file_name)
        parent_arch_hash = self.get_parent_archive_hash()
        arch_hash = get_file_hash(arch_file_name)

        self.archive_stack.append((arch_file_name, extract_path, arch_hash))
        file_size = os.path.getsize(arch_file_name)
        bft = get_book_type(arch_file_name)

        self.logger.print_log(f'ARCH: {arch_file_name}', options=('blue',), linesep='')
        self.logger.print_log(f' ({arch_hash})', options=('yellow',))


        self.db.add_new_archive(arch_logical_name, file_size, arch_hash, parent_arch_hash, bft)

        self.update_logical_path()
        pass

    def on_archive_leave(self):
        self.archive_stack.pop()
        self.update_logical_path()
        pass

    def get_logical_name(self, file_name: str):
        if self.current_logical_path:
            afp, ep, h = self.archive_stack[-1]
            rel_path = os.path.relpath(file_name, ep)
            file_name = os.path.join(self.current_logical_path, rel_path)
        return file_name

    def on_bad_archive(self, f: str, message: str):
        lfn = self.get_logical_name(f)
        self.db.add_bad_file(lfn,
                                      get_file_hash(f),
                                      get_book_type(f),
                                      self.get_parent_archive_hash())
        self.logger.print_err(f'BAD ARCHIVE: {lfn}')
        self.logger.write_log(message)

    def on_bad_book(self, f: str, message: str):
        lfn = self.get_logical_name(f)
        self.db.add_bad_file( lfn,
                              get_file_hash(f),
                              get_book_type(f),
                              self.get_parent_archive_hash())
        self.logger.print_err(f'BAD BOOK: {lfn}')
        self.logger.write_log(message)

    def on_book(self, f: str, b: BookInfo):
        bft = get_book_type(f)

        if bft == BookFileType.NONE:
            return

        b.name = self.get_logical_name(f)
        parent_arch_hash = self.get_parent_archive_hash()
        self.db.add_new_book(b, parent_arch_hash)
        self.logger.print_log(f'BOOK: {b.name}', options=('green',), linesep='')
        self.logger.print_log(f' ({b.hash_value})', options=('yellow',))


    def on_scan_file(self, file_name: str, scan_param):
        self.terminator.check_exit()
        bft = get_book_type(file_name)
        if bft == BookFileType.NONE:
            return

        lfn = self.get_logical_name(file_name)

        # Test if file name is utf-8, and we can work with it.
        # Some archive may produce such names
        res, mod_lfn = test_unicode_string(lfn)
        if not res:
            self.logger.print_err(f'BAD FILE NAME: {mod_lfn}')
            self.db.add_bad_file(mod_lfn,
                                 get_file_hash(file_name),
                                 bft,
                                 self.get_parent_archive_hash())
            return

        if self.db.is_scanned_file(lfn, bft):
            return

        self.logger.print_diagnostic(f'SCAN LFN:  {lfn}')
        self.logger.print_diagnostic(f'SCAN FILE: {file_name}')

        file_hash = get_file_hash(file_name)
        if not self.db.is_processed_file(file_hash, bft):
            bp = self.processor_map[bft]
            try:
                bp.process_file(file_name, file_hash)
            except RuntimeError as e:
                bp.on_bad_callback(file_name, str(e))
        else:
            parent_arch_hash = self.get_parent_archive_hash()
            if bft in book_archive_types:
                self.db.add_existing_archive(self.get_logical_name(file_name), file_hash, parent_arch_hash)
            else:
                self.db.add_existing_book(self.get_logical_name(file_name), file_hash, parent_arch_hash)
