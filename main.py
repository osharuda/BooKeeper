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

from config_file import BooKeeperConfig
from database import *
from scanner import Scanner
from tools import *
from logger import *
import sys

# Paths
#ram_drive_path = '/mnt/ramdrive'
#log_file = '/mnt/SHARE/bookeeper/scan.log'
#db_file_name = "bookgroomer.db"

#library_path   = '/media/oleg/DATA/Books'
#library_path   = '/mnt/SHARE/bookeeper/test'
#language_option = 'eng+rus'

config = BooKeeperConfig(sys.argv[1])
logger = Logger(log_file=config.log_file_name, level=config.log_level)

if not is_ramdrive_mounted(config.ram_drive_path):
    logger.print_err(f'ERROR: Ram drive "{config.ram_drive_path}" is not mounted.')
    quit(1)

db = BooKeeperDB(db_file_name=config.db_file_name, override_db = False)

for lp in config.libraries:
    logger.print_log(f'[LIBRARY] {lp}')
    scanner = Scanner(library_path=lp,
                      ram_drive_path=config.ram_drive_path,
                      language_option=config.language_option)
    scanner.scan()

