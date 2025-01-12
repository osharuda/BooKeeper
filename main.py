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
import shutil

from config_file import BooKeeperConfig
from database import *
from scanner import Scanner
from tools import *
from logger import *
import sys

config = BooKeeperConfig(sys.argv[1])
logger = Logger(log_file=config.log_file_name, level=config.log_level)

if not is_ramdrive_mounted(config.ram_drive_path):
    logger.print_err(f'ERROR: Ram drive "{config.ram_drive_path}" is not mounted.')
    quit(1)
elif config.clear_ram_drive_on_start:
    for p in glob.glob(os.path.join(config.ram_drive_path, '*')):
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.isfile(p):
            os.unlink(p)

db = BooKeeperDB(db_file_name=config.db_file_name, override_db = config.delete_db_on_start)

for lp in config.libraries:
    logger.print_log(f'[LIBRARY] {lp}')
    scanner = Scanner(library_path=lp,
                      ram_drive_path=config.ram_drive_path,
                      language_option=config.language_option,
                      delete_artifacts=config.delete_artifacts)
    scanner.scan()

