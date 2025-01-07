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
from os.path import basename

from processors.proc_base import *
from tools import *
import re
import shutil

class Arch_PROC(Book_PROC):
    def __init__(self,
                 tmpdir: str,
                 lang_opt: str,
                 delete_artifacts: bool,
                 on_scan_file: Callable[[str, str], None],
                 on_book_callback: Callable[[str, BookInfo], None],
                 on_archive_enter: Callable[[str, str, str], None],
                 on_archive_leave: Callable[None, None],
                 on_bad_callback: Callable[[str, str], None],
                 arch_type: BookFileType):
        super().__init__(tmpdir, lang_opt, delete_artifacts, on_book_callback, on_bad_callback)
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

    @staticmethod
    def get_unpack_sequence(file_name: str):
        path_components = file_name.split(os.sep)
        current_path = os.sep if len(path_components[0])==0 else ''
        result = list()
        last_path = None

        for c in path_components:
            current_path = os.path.join(current_path, c)
            bt = get_book_type(current_path)
            if bt in book_archive_types:
                last_path = current_path
                result.append(last_path)

        if last_path != current_path:
            result.append(current_path)

        return result

    def unpack_file(self, file_name: str) -> str:
        """
        Args:
            file_name: Logical file name to extract
        Returns:
            Extracted file path
        """

        archive_hierarchy = Arch_PROC.get_unpack_sequence(file_name)

        levels = len(archive_hierarchy)
        if levels <= 0:
            raise RuntimeError('At least one file must be specified')
        elif levels == 1:
            return archive_hierarchy[0]


        arch = archive_hierarchy[0]
        last_archive = arch
        extract_dirs = list()

        for pos in range(1, levels):
            fn = archive_hierarchy[pos]
            rel_name = os.path.relpath(fn, last_archive)
            last_archive = fn
            extract_path = self.make_tmp_dir()
            extract_dirs.append(extract_path)
            print(arch)

            arch = self.unpack_file_no_recursive_archives(os.path.join(arch, rel_name), extract_path)

        # Move to the root of the ram drive
        dst_file_name = os.path.join(self.temp_dir, os.path.basename(arch))

        if os.path.isfile(dst_file_name):
            os.unlink(dst_file_name)

        shutil.move(arch, dst_file_name)

        # Clean other artifacts
        if self.delete_artifacts:
            for d in extract_dirs:
                shutil.rmtree(d)

        return dst_file_name




    def unpack_file_no_recursive_archives(self, logical_file_name: str, extract_path: str) -> str:
        """
        Unpacks single file from archive without recursion.
        Args:
            archive_name:
            exract_path:

        Returns:
        """
        # Split logical file name up to the first archive name
        path_components = logical_file_name.split(os.sep)
        current_path = ''
        archive_path = ''
        result = None
        bt = BookFileType.NONE
        if len(path_components[0])==0:
            current_path = os.sep # Linux, need to put root first

        pos = 0
        for c in path_components:
            current_path = os.path.join(current_path, c)
            pos += 1

            if os.path.isfile(current_path):
                bt = get_book_type(current_path)
                if bt not in book_archive_types:
                    raise RuntimeError(f'Unsupported archive type: {current_path}')
                else:
                    archive_path = current_path
                    break
        inner_rel_path = os.sep.join(path_components[pos:])

        match bt:
            case BookFileType.ARCH_7Z:
                result = self.unpack_file_7z(archive_path, inner_rel_path, extract_path)
            case BookFileType.ARCH_ZIP:
                result = self.unpack_file_zip(archive_path, inner_rel_path, extract_path)
            case BookFileType.ARCH_RAR:
                result = self.unpack_file_rar(archive_path, inner_rel_path, extract_path)
            case BookFileType.ARCH_TARGZ:
                result = self.unpack_file_tar_gz(archive_path, inner_rel_path, extract_path)

        return result


    def unpack_file_7z(self, archive_name: str, inner_rel_path: str, target_dir: str) -> str:
        """
        Unpack single file from archive (7z)
        Args:
            archive_name: Archive name
            inner_rel_path: Relative file name inside archive without leading separator ('subdir/some_file.pdf').
            target_dir: Target directory to extract file in.

        Returns:
            Extracted file name
        """
        res, code, stdout = run_shell_adv(['7z', 'x', archive_name, inner_rel_path, f'-o{target_dir}'], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {archive_name}({os.sep}{inner_rel_path}).\nError code: {code}\n{stdout}')

        extract_file = os.path.join(target_dir, inner_rel_path)
        destination_file = os.path.join(target_dir, basename(inner_rel_path))
        if inner_rel_path != destination_file:
            shutil.move(extract_file, destination_file)

        return destination_file

    def unpack_file_zip(self, archive_name: str, inner_rel_path: str, target_dir: str) -> str:
        """
        Unpack single file from archive (zip)
        Args:
            archive_name: Archive name
            inner_rel_path: Relative file name inside archive without leading separator ('subdir/some_file.pdf').
            target_dir: Target directory to extract file in.

        Returns:
            Extracted file name
        """

        res, code, stdout = run_shell_adv(['unzip', archive_name, inner_rel_path, f'-d', target_dir], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {archive_name}({os.sep}{inner_rel_path}).\nError code: {code}\n{stdout}')

        self.add_write_perm_to_dir(target_dir)

        extract_file = os.path.join(target_dir, inner_rel_path)
        destination_file = os.path.join(target_dir, basename(inner_rel_path))
        if inner_rel_path != destination_file:
            shutil.move(extract_file, destination_file)

        return destination_file

    def unpack_file_tar_gz(self, archive_name: str, inner_rel_path: str, target_dir: str) -> str:
        """
        Unpack single file from archive (tar.gz)
        Args:
            archive_name: Archive name
            inner_rel_path: Relative file name inside archive without leading separator ('subdir/some_file.pdf').
            target_dir: Target directory to extract file in.

        Returns:
            Extracted file name
        """
        res, code, stdout = run_shell_adv(['tar', '-xzvf', archive_name, '-C', target_dir, inner_rel_path], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {archive_name}({os.sep}{inner_rel_path}).\nError code: {code}\n{stdout}')

        extract_file = os.path.join(target_dir, inner_rel_path)
        destination_file = os.path.join(target_dir, basename(inner_rel_path))
        if inner_rel_path != destination_file:
            shutil.move(extract_file, destination_file)

        return destination_file

    def unpack_file_rar(self, archive_name: str, inner_rel_path: str, target_dir: str) -> str:
        """
        Unpack single file from archive (rar)
        Args:
            archive_name: Archive name
            inner_rel_path: Relative file name inside archive without leading separator ('subdir/some_file.pdf').
            target_dir: Target directory to extract file in.

        Returns:
            Extracted file name
        """

        res, code, stdout = run_shell_adv(['unrar', 'x', archive_name, inner_rel_path, f'{target_dir}/'], print_stdout=False)
        if not res:
            raise RuntimeError(f'Failed to extract an archive {archive_name}({os.sep}{inner_rel_path}).\nError code: {code}\n{stdout}')

        extract_file = os.path.join(target_dir, inner_rel_path)
        destination_file = os.path.join(target_dir, basename(inner_rel_path))
        if inner_rel_path != destination_file:
            shutil.move(extract_file, destination_file)

        return destination_file


    def make_tmp_dir(self):
        uniq_name = str(self.arch_type)+f'_{self.uniq_counter}'
        self.uniq_counter += 1
        tmp_dir = os.path.join(self.temp_dir, uniq_name)
        if os.path.isdir(tmp_dir) and self.delete_artifacts:
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

