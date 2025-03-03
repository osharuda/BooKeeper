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
import shutil
import sqlite3
import contextlib
from processors.proc_base import *
from processors.processors import BookInfo
from logger import *
import re

class FileErrorCode(IntEnum):
    ERROR_BAD_FILE_NAME = -100
    ERROR_BAD_BOOK = -101
    ERROR_BAD_ARCHIVE = -102


class BooKeeperDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BooKeeperDB, cls).__new__(cls)
            cls._instance.db_file_name = None
            cls._instance.connection = None
            cls._instance.logger = None
            cls._instance.initialize(kwargs['db_file_name'], kwargs['ram_drive_db'], kwargs['override_db'])
        return cls._instance


    def __del__(self):
        if not self.finalized:
            raise RuntimeError('Database is not finalized')


    def finalize(self):
        self.close_db()
        self.logger.print_diagnostic(f'BooKeeperDB destroyed.', console_only=True)

        if self.ram_drive_db:
            self.logger.print_log("Copying database from RAM drive")
            tmp_fn = self.db_file_name+'.bak'
            if os.path.isfile(tmp_fn):
                os.unlink(tmp_fn)

            if os.path.isfile(self.db_file_name):
                shutil.move(self.db_file_name, tmp_fn)

            shutil.copy(self.ram_drive_db, self.db_file_name)

            if os.path.isfile(tmp_fn):
                os.unlink(tmp_fn)

        self.logger.print_log("Database successfully closed.")
        self.finalized = True


    def initialize(self, db_file_name: str, ram_drive_db, override_db = False):
        self.logger = Logger()
        self.db_file_name = db_file_name
        self.db_escape_trans = str.maketrans({"'": "''"})
        self.book_cache = None
        self.file_name_cache = None
        self.ram_drive_db = ram_drive_db
        self.finalized = False
        self.new_book_counter = 0

        if override_db and os.path.isfile(self.db_file_name):
            os.unlink(self.db_file_name)

        if self.ram_drive_db:
            self.logger.print_log("Copying database to RAM drive")
            if os.path.isfile(ram_drive_db):
                os.unlink(self.ram_drive_db)
            if os.path.isfile(self.db_file_name):
                shutil.copy(self.db_file_name, self.ram_drive_db)

        db_file = self.ram_drive_db if self.ram_drive_db else self.db_file_name
        self.connection = sqlite3.connect(db_file)
        self.init_db()
        self.connection.commit()
        self.update_cache()
        self.logger.print_diagnostic('BooKeeperDB created.', console_only=True)


    def init_db(self):
        with contextlib.closing(self.connection.cursor()) as cursor:
            lines = cursor.execute("select count(ALL) from sqlite_master").fetchone()[0]
            if lines!=0:
                self.logger.print_diagnostic(f'Database is already initialized.')
                return

            self.logger.print_diagnostic(f'Initializing db ...')
            cursor.execute("""CREATE TABLE archives( 
hash string primary key,
file_type int,
size sqlite_int64
);""")

            cursor.execute("""CREATE TABLE archive_files( 
id integer primary key,
file_name string,
hash string,
parent_arch_hash string,
status int,
foreign key(parent_arch_hash) references archives(hash),
foreign key(hash) references archives(hash)
);""")

            cursor.execute("""CREATE TABLE books( 
hash string primary key,
size sqlite_int64,
ocr bool,
booktype int,
page_count int,
text_data string,
tokens string
);""")

            cursor.execute("""CREATE TABLE book_files( 
id integer primary key,
file_name string,
archive_hash string,
hash string,
status int,
foreign key(archive_hash) references archives(hash),
foreign key(hash) references books(hash)
);""")


            cursor.execute("""CREATE TABLE bad_files( 
id int  primary key,
file_name string,
file_type int,
hash string,
archive_hash string,
error_code int,
status int,
foreign key(archive_hash) references archives(hash)
);""")

            cursor.execute("""CREATE TABLE other_paths( 
id integer primary key,
path string,
status int
);""")

            cursor.execute("""CREATE TABLE other_files( 
id integer primary key,
path_id int,
basename string,
extension string,
size sqlite_int64,
hash string,
status int,
foreign key(path_id) references other_paths(id)
);""")

            cursor.execute("""create unique index indx_book_files_on_file_name on book_files(file_name);
""")

            cursor.execute("""create unique index indx_archive_files_on_file_name on archive_files(file_name);
""")

            cursor.execute("""create unique index indx_other_files_on_pid_bn on other_files(path_id, basename);
""")

            cursor.execute("""create unique index indx_other_paths_path on other_paths(path);
""")

        self.connection.commit()


    def close_db(self):
        #self.connection.commit()
        self.connection.close()


    def escape_string(self, s: str):
        return s.translate(self.db_escape_trans)


    def add_update_bad_file(self,
                            file_name: str,
                            file_hash: str,
                            file_type: BookFileType,
                            parent_arch_hash: str,
                            error_code: FileErrorCode):

        if not parent_arch_hash:
            parent_arch = "NULL"
        else:
            parent_arch = f"'{parent_arch_hash}'"

        do_update = self.is_bad_file(file_name)
        if do_update:
            query = f"""update bad_files 
set
file_type = {int(file_type)},
hash = '{file_hash}',
archive_hash = {parent_arch},
error_code = {error_code},
status = 0
where
file_name = '{self.escape_string(file_name)}'
"""
        else:
            query = f"""insert into bad_files (file_name, file_type, hash, archive_hash, error_code, status)
values( 
'{self.escape_string(file_name)}',
{int(file_type)},
'{file_hash}',
{parent_arch},
{error_code},
0);"""

        with contextlib.closing(self.connection.cursor()) as cursor:
            try:
                cursor.execute(query)
                cursor.connection.commit()
            except sqlite3.Error as e:
                raise RuntimeError(f'Failed to add/update into bad_files.\n{e}')


    def add_new_archive(self,
                    file_name: str,
                    file_size: int,
                    file_hash: str,
                    parent_arch: str,
                    bft: BookFileType):
        if not self.is_processed_archive(file_hash):
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
        escaped_file_name = self.escape_string(file_name)
        try:
            with contextlib.closing(self.connection.cursor()) as cursor:
                query = f"""select id, status from archive_files where file_name='{escaped_file_name}' limit 1;"""
                res = cursor.execute(query).fetchone()
                if res:
                    arch_id, status = res
                    if status != 0:
                        update_query = f"""update archive_files 
    set 
    status=0
    where 
    id={arch_id}
    """
                        cursor.execute(update_query)
                else:

                        if not parent_arch_hash:
                            parent_arch = "NULL"
                        else:
                            parent_arch = f"'{parent_arch_hash}'"
                        cursor.execute(f"""insert into archive_files (file_name, parent_arch_hash, hash, status)
                                                               values('{escaped_file_name}', {parent_arch}, '{file_hash}', 0);""")


                cursor.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f'Failed to insert/update into archive_files.\n{e}')


    def add_new_book(self,
                    bi: BookInfo,
                    parent_arch_hash: str):
        if not self.is_processed_book(bi.hash_value):
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
                    self.new_book_counter += 1
                except sqlite3.Error as e:
                    raise RuntimeError(f'Failed to insert into books.\n{e}')

        self.add_existing_book(bi.name, bi.hash_value, parent_arch_hash)


    def add_existing_book(self,
                          file_name: str,
                          file_hash: str,
                          parent_arch_hash: str):
        escaped_file_name = self.escape_string(file_name)
        try:
            with contextlib.closing(self.connection.cursor()) as cursor:
                query = f"""select id, status from book_files where file_name='{escaped_file_name}' limit 1;"""
                res = cursor.execute(query).fetchone()
                if res:
                    file_id, status = res
                    if status != 0:
                        update_query = f"""update book_files set status=0 where id={file_id}"""
                        cursor.execute(update_query)
                else:
                    if not parent_arch_hash:
                        parent_arch_hash = "NULL"
                    else:
                        parent_arch_hash = f"'{parent_arch_hash}'"
                    cursor.execute(f"""insert into book_files (file_name, archive_hash, hash, status)
                                   values('{escaped_file_name}', {parent_arch_hash}, '{file_hash}', 0);""")
                cursor.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f'Failed to insert into book_files.\n{e}')


    def is_scanned_archive(self, file_name: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            rc = cursor.execute(f"""select count(*) from 
                                    archive_files where file_name = '{self.escape_string(file_name)}';
                                    """).fetchone()[0]
        return rc > 0

    def mark_archive_as_existent(self, file_name: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            fn = self.escape_string(os.path.abspath(file_name))
            pattern = f"{fn}{os.sep}%"

            query_paths = f"""select id from other_paths where path like '{pattern}';"""
            query_res = cursor.execute(query_paths).fetchall()
            path_ids = list(map(lambda x: str(x[0]), query_res))
            path_id_param = ','.join(path_ids)


            update_books = f"""update book_files set status=0 where file_name like '{pattern}';"""
            cursor.execute(update_books)

            update_archives = f"""update archive_files set status=0 where file_name like '{pattern}';"""
            cursor.execute(update_archives)

            update_archives = f"""update archive_files set status=0 where file_name = '{fn}';"""
            cursor.execute(update_archives)

            update_other = f"""update other_files set status=0 where path_id in ({path_id_param});"""
            cursor.execute(update_other)

            cursor.connection.commit()


    def is_scanned_book(self, file_name: str):

        res, mod_file_name = test_unicode_string(file_name)
        if not res:
            file_name = mod_file_name

        with contextlib.closing(self.connection.cursor()) as cursor:
            query = f"""select count(*) from 
                           book_files where file_name = '{self.escape_string(file_name)}';
                           """
            rc = cursor.execute(query).fetchone()[0]
        return rc > 0

    def mark_book_as_existent(self, file_name: str):
        with contextlib.closing(self.connection.cursor()) as cursor:
            query = f"""update book_files set status=0 where file_name='{self.escape_string(file_name)}';"""
            cursor.execute(query)
            cursor.connection.commit()

    def is_bad_file(self, file_name: str):
        res, mod_file_name = test_unicode_string(file_name)
        if not res:
            file_name = mod_file_name

        with contextlib.closing(self.connection.cursor()) as cursor:
            query = f"""select count(*) from 
                           bad_files where file_name = '{self.escape_string(file_name)}';
                           """
            rc = cursor.execute(query).fetchone()[0]
        return rc > 0


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
        with contextlib.closing(self.connection.cursor()) as cursor:
            rc = cursor.execute(f"""select count(*) from 
                                    books where hash='{file_hash}';
                                    """).fetchone()[0]
        return rc > 0


    def update_cache(self):
        self.book_cache = None
        self.file_name_cache = None # Translate hash value to the list of file names
        self.archive_cache = None   # Translate file name to the parent archive hash

        try:
            with contextlib.closing(self.connection.cursor()) as cursor:
                query = """select books.hash, books.text_data, books.booktype from books;"""
                query_res = cursor.execute(query).fetchall()
                self.book_cache = list(map(lambda t: (t[0], str(t[1]), t[2]), query_res))

                query2 = """select hash, archive_hash, file_name from book_files;"""
                query2_res = cursor.execute(query2).fetchall()

                self.archive_cache = dict()
                temp_file_name_cache = dict()
                for h, ah, fn in query2_res:
                    self.archive_cache[fn] = ah
                    if h not in temp_file_name_cache.keys():
                        temp_file_name_cache[h] = set()

                    temp_file_name_cache[h].add(fn)

                self.file_name_cache = dict()
                for h, fs in temp_file_name_cache.items():
                    self.file_name_cache[h] = list(fs)

                res = True
        except Exception as e:
            res = False

        return res


    def search_books_in_cache(self, sl: list[str]):
        file_list = list()
        hash_list = list()
        text_data_list = list()
        text_data_dict = dict()
        results_list = list()
        spans_list = list()
        archive_list = list()
        book_type_list = list()
        res = False

        # Find all books that matches every single search query
        for s in sl:
            if not s:
                continue

            search_re = re.compile(re.escape(s), re.IGNORECASE)

            match_books = dict()
            for h,t,bt in self.book_cache:
                match_count = 0
                match_spans = list()
                for m in re.finditer(search_re, t):
                    match_count += 1
                    match_spans.append(m.span())

                if match_count:
                    rang = float ( match_count * len(s) ) / float ( (len(t) + 1) )
                    match_books[h] = ( rang, match_spans, bt )
                    text_data_dict[h] = t
            results_list.append(match_books)

        # Build intersection of all results, recalculating (multiplication) rangs.
        match_books = results_list[0]
        for i in range(1, len(results_list)):
            next_res = results_list[i]
            intersect_keys = match_books.keys() & next_res.keys()
            remove_keys = list()
            for k in match_books.keys():
                if k not in intersect_keys:
                    remove_keys.append(k)
                else:
                    prev_rang, prev_spans = match_books[k]
                    next_rang, next_spans = next_res[k]
                    rang = prev_rang * next_rang

                    spans = prev_spans + next_spans
                    spans = sorted(spans, key=lambda kv: kv[0])
                    match_books[k] = (rang, spans)

            for k in remove_keys:
                match_books.pop(k)

        # Sort by rang
        sorted_match = sorted(match_books.items(), key=lambda kv: kv[1][0], reverse=True)

        for h, (rang, spans, bt) in sorted_match:
            res = True
            fl = self.file_name_cache.get(h, [])
            cnt = len(fl)

            for f in fl:
                archive_list.append(self.is_file_archived(f))

            hash_list = hash_list + [h] * cnt
            book_type_list = book_type_list + [bt] * cnt
            spans_list = spans_list + [spans] * cnt
            file_list = file_list + fl
            t = text_data_dict[h]
            text_data_list = text_data_list + [t] * cnt

        return res, file_list, hash_list, archive_list, text_data_list, spans_list, book_type_list


    def get_book_info(self, hash: str):

        query = f"""select size, ocr, booktype, page_count, text_data, tokens from books where hash='{self.escape_string(hash)}';"""
        query_res = None
        try:
            with contextlib.closing(self.connection.cursor()) as cursor:
                query_res = cursor.execute(query).fetchone()
        except Exception as e:
            pass

        return query_res

    def is_file_archived(self, file_name: str):
        return self.archive_cache[file_name] is not None

    def rename_file(self, old_file_name: str, new_file_name: str):
        file_name_update_query = f"""update book_files set file_name='{self.escape_string(new_file_name)}' where file_name='{old_file_name}';"""
        with contextlib.closing(self.connection.cursor()) as cursor:
            cursor.execute(file_name_update_query)
            cursor.connection.commit()

    def add_get_path(self, path: str):
        path_query = f"""select other_paths.id, other_paths.status from other_paths where path='{path}';"""
        with contextlib.closing(self.connection.cursor()) as cursor:
            res = cursor.execute(path_query).fetchone()

            if not res:
                insert_path_query = f"""insert into other_paths (path, status) values('{path}', 0);"""
                cursor.execute(insert_path_query)
                cursor.connection.commit()

                res = cursor.execute(path_query).fetchone()

            path_id, path_status = res

            if path_status != 0:
                    path_update_query = f"""update other_paths set status=0 where id={path_id}"""
                    cursor.execute(path_update_query)
                    cursor.connection.commit()

        return path_id


    def add_get_other_file(self, logical_file_name: str, file_name: str, size: int):
        escaped_file_name = self.escape_string(logical_file_name)
        file_path, basename = os.path.split(escaped_file_name)
        path_id = self.add_get_path(file_path)
        new_file = False

        file_query = f"""select id, status from other_files where path_id={path_id} and basename='{basename}';"""
        with contextlib.closing(self.connection.cursor()) as cursor:
            res = cursor.execute(file_query).fetchone()
            if not res:
                bn, ext = split_file_name(logical_file_name)
                file_hash = get_file_hash(file_name)
                insert_file_query = f"""insert into other_files (path_id, basename, extension, size, hash, status)
values({path_id}, '{basename}', '{self.escape_string(ext.lower())}',{size}, '{file_hash}', 0);"""
                cursor.execute(insert_file_query)
                cursor.connection.commit()

                res = cursor.execute(file_query).fetchone()
                new_file = True

            file_id, status = res

            if status != 0:
                file_update_query = f"""update other_files set status=0 where id={file_id}"""
                cursor.execute(file_update_query)
                cursor.connection.commit()

        return file_id, new_file


    def prepare_scan(self):
        self.new_book_counter = 0
        with contextlib.closing(self.connection.cursor()) as cursor:
            query = """update archive_files set status = -1;"""
            cursor.execute(query)

            query = """update book_files set status = -1;"""
            cursor.execute(query)

            #query = """update bad_files set status = -1;"""
            #cursor.execute(query)

            query = """update other_files set status = -1;"""
            cursor.execute(query)

            #query = """update other_paths set status = -1;"""
            #cursor.execute(query)

            cursor.connection.commit()

            pass

    def post_scan(self):
        with contextlib.closing(self.connection.cursor()) as cursor:
            query = """delete from archive_files where status = -1;"""
            cursor.execute(query)

            query = """delete from book_files where status = -1;"""
            cursor.execute(query)

            query = """delete from other_files where status = -1;"""
            cursor.execute(query)

            cursor.connection.commit()

        if self.new_book_counter:
            self.logger.print_log(f"{self.new_book_counter} new books added.")



    def get_sql_cursor(self, query: str):
        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor


    def execute(self, query):
        with contextlib.closing(self.connection.cursor()) as cursor:
            cursor.execute(query)
            cursor.connection.commit()


    def get_cursor(self):
        return self.connection.cursor()

