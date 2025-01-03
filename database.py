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

import sqlite3
import contextlib
from processors.proc_base import *
from processors.processors import BookInfo
from logger import *

class BooKeeperDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BooKeeperDB, cls).__new__(cls)
            cls._instance.db_file_name = None
            cls._instance.connection = None
            cls._instance.logger = None
            cls._instance.initialize(kwargs['db_file_name'], kwargs['override_db'])
        return cls._instance

    def __del__(self):
        self.close_db()
        self.logger.print_diagnostic(f'BooKeeperDB destroyed.', console_only=True)


    def initialize(self, db_file_name: str, override_db = False):
        self.logger = Logger()
        self.db_file_name = db_file_name
        self.db_escape_trans = str.maketrans({"'": "''"})

        if override_db and os.path.isfile(self.db_file_name):
            os.unlink(self.db_file_name)

        self.connection = sqlite3.connect(self.db_file_name)
        self.init_db()
        self.connection.commit()
        self.logger.print_diagnostic('BooKeeperDB created.', console_only=True)


    def init_db(self):
        with contextlib.closing(self.connection.cursor()) as cursor:
            lines = cursor.execute("select count(ALL) from sqlite_master").fetchone()[0]
            if lines!=0:
                self.logger.print_diagnostic(f'Database is already initialized.')
                return

            self.logger.print_diagnostic(f'Initializing db ...')
            cursor.execute("""CREATE TABLE archives( hash string primary key,
                                                  file_type int,
                                                  size sqlite_int64);""")

            cursor.execute("""CREATE TABLE archive_files( id integer primary key,
                                                  file_name string,
                                                  hash string,
                                                  parent_arch_hash string,
                                                  foreign key(parent_arch_hash) references archives(hash),
                                                  foreign key(hash) references archives(hash));""")

            cursor.execute("""CREATE TABLE books(   hash string primary key,
                                                    size sqlite_int64,
                                                    ocr bool,
                                                    booktype int,
                                                    page_count int,
                                                    text_data string,
                                                    tokens string
                                                  );""")

            cursor.execute("""CREATE TABLE book_files( id integer primary key,
                                                  file_name string,
                                                  archive_hash string,
                                                  hash string,
                                                  foreign key(archive_hash) references archives(hash),
                                                  foreign key(hash) references books(hash));""")


            cursor.execute("""CREATE TABLE bad_files( id int  primary key,
                                                  file_name string,
                                                  file_type int,
                                                  hash string,
                                                  archive_hash string,
                                                  foreign key(archive_hash) references archives(hash));""")

        self.connection.commit()

    def close_db(self):
        self.connection.commit()
        self.connection.close()

    def escape_string(self, s: str):
        return s.translate(self.db_escape_trans)

    def add_bad_file(self,
                     file_name: str,
                     file_hash: str,
                     file_type: BookFileType,
                     parent_arch_hash: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            try:
                if not parent_arch_hash:
                    parent_arch = "NULL"
                else:
                    parent_arch = f"'{parent_arch_hash}'"
                cursor.execute(f"""insert into bad_files (file_name, file_type, hash, archive_hash)
                                                  values( '{self.escape_string(file_name)}',
                                                           {int(file_type)},
                                                          '{file_hash}',
                                                           {parent_arch});""")
                cursor.connection.commit()
            except sqlite3.Error as e:
                raise RuntimeError(f'Failed to insert into bad_files.\n{e}')



    def add_new_archive(self,
                    file_name: str,
                    file_size: int,
                    file_hash: str,
                    parent_arch: str,
                    bft: BookFileType):
        with contextlib.closing(self.connection.cursor()) as cursor:
            try:
                cursor.execute(f"""insert into archives (hash,          file_type, size)
                                                  values('{file_hash}', {bft},     {file_size} );""")
                cursor.connection.commit()
            except sqlite3.Error as e:
                raise RuntimeError(f'Failed to insert into archives.\n{e}')

        self.add_existing_archive(file_name, file_hash, parent_arch)


    def add_existing_archive(self,
                    file_name: str,
                    file_hash: str,
                    parent_arch_hash: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            try:
                if not parent_arch_hash:
                    parent_arch = "NULL"
                else:
                    parent_arch = f"'{parent_arch_hash}'"
                cursor.execute(f"""insert into archive_files (file_name,     parent_arch_hash, hash)
                                                       values('{self.escape_string(file_name)}', {parent_arch},    '{file_hash}');""")
            except sqlite3.Error as e:
                raise RuntimeError(f'Failed to insert into archive_files.\n{e}')

            cursor.connection.commit()


    def add_new_book(self,
                    bi: BookInfo,
                    parent_arch_hash: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            try:
                cursor.execute(f"""insert into books (hash, size, ocr, booktype, page_count, text_data, tokens)
                                                      values('{bi.hash_value}', 
                                                             {bi.size}, 
                                                             {int(bi.ocr)}, 
                                                             {bi.book_type}, 
                                                             {bi.page_count}, 
                                                             '{bi.text_data}',
                                                             '');""")

                cursor.connection.commit()
            except sqlite3.Error as e:
                raise RuntimeError(f'Failed to insert into books.\n{e}')

        self.add_existing_book(bi.name, bi.hash_value, parent_arch_hash)




    def add_existing_book(self,
                          file_name: str,
                          file_hash: str,
                          parent_arch_hash: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            try:
                if not parent_arch_hash:
                    parent_arch_hash = "NULL"
                else:
                    parent_arch_hash = f"'{parent_arch_hash}'"
                cursor.execute(f"""insert into book_files (file_name, archive_hash, hash)
                                                       values('{self.escape_string(file_name)}', {parent_arch_hash},    '{file_hash}');""")
            except sqlite3.Error as e:
                raise RuntimeError(f'Failed to insert into book_files.\n{e}')

            cursor.connection.commit()

    def is_scanned_archive(self, file_name: str):
        rc = 0
        with contextlib.closing(self.connection.cursor()) as cursor:
            rc = cursor.execute(f"""select count(*) from 
                                    archive_files where file_name = '{self.escape_string(file_name)}';
                                    """).fetchone()[0]

        return rc > 0

    def is_scanned_book(self, file_name: str):

        res, mod_file_name = test_unicode_string(file_name)
        if not res:
            file_name = mod_file_name

        with contextlib.closing(self.connection.cursor()) as cursor:
            rc = cursor.execute(f"""select count(*) from 
                                    book_files where file_name = '{self.escape_string(file_name)}';
                                    """).fetchone()[0]

        return rc > 0

    def is_scanned_file(self, file_name: str, bft: BookFileType):
        if bft in book_archive_types:
            return self.is_scanned_archive(file_name)
        else:
            return self.is_scanned_book(file_name)


    def is_processed_file(self, file_hash: str, bft: BookFileType) -> bool:
        if bft in book_archive_types:
            return self.is_processed_archive(file_hash)
        else:
            return self.is_processed_book(file_hash)


    def is_processed_archive(self, file_hash: str) -> bool:
        rc = 0
        with contextlib.closing(self.connection.cursor()) as cursor:
            rc = cursor.execute(f"""select count(*) from 
                                    archives where hash='{file_hash}';
                                    """).fetchone()[0]

        return rc > 0

    def is_processed_book(self, file_hash: str) -> bool:
        rc = 0
        with contextlib.closing(self.connection.cursor()) as cursor:
            rc = cursor.execute(f"""select count(*) from 
                                    books where hash='{file_hash}';
                                    """).fetchone()[0]

        return rc > 0