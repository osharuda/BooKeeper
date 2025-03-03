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

from database import *
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
        self.new_prefix = '[⚡] '
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
        """
        Run library scan
        """
        self.terminator = Terminator()
        self.db.prepare_scan()
        scan_directory(self.library_path, on_file=self.on_scan_file)
        self.db.post_scan()


    def update_logical_path(self):
        """
        Updates self.current_logical_path if we are inside archive.
        For internal use.
        """
        self.current_logical_path = ''
        if len(self.archive_stack) > 0:
            tmp = '/'
            self.current_logical_path = '/'
            for (afn, ep, h) in self.archive_stack:
                rel_path = os.path.relpath(afn, tmp)
                self.current_logical_path = os.path.join(self.current_logical_path, rel_path)
                tmp = ep


    def get_parent_archive_hash(self) -> str:
        """
        Returns: Current archive (the one on the top of the archives stack) or empty string if not in archive.
        """
        parent_arch_hash = ''
        if len(self.archive_stack):
            parent_arch_hash = self.archive_stack[-1][2]

        return parent_arch_hash


    def on_archive_enter(self, arch_file_name: str, extract_path: str, file_hash: str):
        """
        Callback to be called every time scanner entered the archive.
        Args:
            arch_file_name: Archive file name (real file system name).
            extract_path: Path where archive was extracted.
            file_hash: Archive hash.
        """
        arch_logical_name = self.get_logical_name(arch_file_name)
        parent_arch_hash = self.get_parent_archive_hash()

        self.archive_stack.append((arch_file_name, extract_path, file_hash))
        file_size = os.path.getsize(arch_file_name)
        bft = get_book_type(arch_file_name)

        self.logger.print_log(f'{self.new_prefix}ARCH: {arch_file_name}', options=('blue',), linesep='')
        self.logger.print_log(f' ({file_hash})', options=('yellow',))

        self.db.add_new_archive(arch_logical_name, file_size, file_hash, parent_arch_hash, bft)
        self.update_logical_path()


    def on_archive_leave(self):
        """
        Callback to be called every time scanner leaves the archive.
        """
        self.archive_stack.pop()
        self.update_logical_path()


    def get_logical_name(self, file_name: str):
        """
        Returns logical file name. Logical file name takes into account archives in the way all nested archives are
        treated as a directories.
        Args:
            file_name: File name to be converted into logical file name. It could be either a name of the file located
            in library unpacked, or file name within unpacked archive somewhere on RAM drive.

        Returns: Logical file name.

        """
        if self.current_logical_path:
            afp, ep, h = self.archive_stack[-1]
            rel_path = os.path.relpath(file_name, ep)
            file_name = os.path.join(self.current_logical_path, rel_path)
        return file_name


    def on_bad_archive(self, file_name: str, message: str):
        """
        Callback to be called every time scanner entered the archive.
        Args:
            file_name: Bad archive file name (real file system name).
            message: Error message
        """
        lfn = self.get_logical_name(file_name)
        self.db.add_update_bad_file(lfn,
                                    get_file_hash(file_name),
                                    get_book_type(file_name),
                                    self.get_parent_archive_hash(),
                                    FileErrorCode.ERROR_BAD_ARCHIVE)
        self.logger.print_err(f'BAD ARCHIVE: {lfn}')
        self.logger.write_log(message)


    def on_bad_book(self, file_name: str, message: str):
        """
        Callback to be called every time scanner encounters a bad book.
        Args:
            file_name: Bad book file name (real file system name).
            message: Error message
        """
        lfn = self.get_logical_name(file_name)
        self.db.add_update_bad_file(lfn,
                                    get_file_hash(file_name),
                                    get_book_type(file_name),
                                    self.get_parent_archive_hash(),
                                    FileErrorCode.ERROR_BAD_FILE_NAME)
        self.logger.print_err(f'BAD BOOK: {lfn}')
        self.logger.write_log(message)


    def on_book(self, file_name: str, b: BookInfo):
        """
        Callback to be called every time scanner encounters a (good) book.
        Args:
            file_name: Book file name (real file system name).
            b: Book information
        """
        b.name = self.get_logical_name(file_name)
        parent_arch_hash = self.get_parent_archive_hash()
        self.db.add_new_book(b, parent_arch_hash)
        self.logger.print_log(f'{self.new_prefix}BOOK: {b.name}', options=('green',), linesep='')
        self.logger.print_log(f' ({b.hash_value})', options=('yellow',))



    def check_and_process_existing(self, lfn: str, file_name: str, bft: BookFileType):
        if bft==BookFileType.NONE:
            file_id, new_file = self.db.add_get_other_file(lfn, file_name, os.path.getsize(file_name))
            if new_file:
                self.logger.print_diagnostic(f'{self.new_prefix}OTHER: {lfn}', options=('dark_grey', None, ['dark']))
            else:
                self.logger.print_diagnostic(f'OTHER: {lfn}', options=('dark_grey',None,['dark']))
            return

        if self.db.is_bad_file(lfn):
            return True

        if bft in book_archive_types:
            res = self.db.is_scanned_archive(lfn)
            if not res:
                return False
            self.db.mark_archive_as_existent(lfn)
            self.logger.print_log(f'ARCH: {lfn}', options=('dark_grey',None,['dark']))

        else:
            res = self.db.is_scanned_book(lfn)
            if not res:
                return False
            self.db.mark_book_as_existent(lfn)
            self.logger.print_log(f'BOOK: {lfn}', options=('dark_grey', None, ['dark']))
        return res


    def on_scan_file(self, file_name: str, scan_param):
        """
        Callback to be called every time scanner encounters some file.
        Args:
            file_name: Book file name (real file system name).
            scan_param: Scan parameter - unused here
        """
        self.terminator.check_exit()
        file_name = os.path.abspath(file_name)
        bft = get_book_type(file_name)
        lfn = self.get_logical_name(file_name)

        # Test if file name is utf-8, and we use it further.
        # Beware: some archives may produce non utf-8 names, which may not be handled.
        res, mod_lfn = test_unicode_string(lfn)
        if not res:
            self.logger.print_err(f'BAD FILE NAME: {mod_lfn}')
            file_hash = get_file_hash(file_name)
            self.db.add_update_bad_file(mod_lfn,
                                        file_hash,
                                        bft,
                                        self.get_parent_archive_hash(),
                                        FileErrorCode.ERROR_BAD_BOOK)
            return

        if self.check_and_process_existing(lfn, file_name, bft):
            return

        if bft == BookFileType.NONE:
            return

        self.logger.print_diagnostic(f'SCAN LFN:  {lfn}')
        self.logger.print_diagnostic(f'SCAN FILE: {file_name}')

        file_hash = get_file_hash(file_name)
        if self.db.is_processed_file(file_hash, bft) and bft not in book_archive_types:
            parent_arch_hash = self.get_parent_archive_hash()
            self.logger.print_log(f'BOOK: {lfn}', options=('green', None, ['dark']))
            self.db.add_existing_book(lfn, file_hash, parent_arch_hash)
        else:
            bp = self.processor_map[bft]
            try:
                bp.process_file(file_name, file_hash)
            except RuntimeError as e:
                bp.on_bad_callback(file_name, str(e))
