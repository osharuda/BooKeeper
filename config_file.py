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

import json
import os


class BooKeeperConfig:
    def __init__(self, config_file_name):
        try:
            with open(os.path.abspath(config_file_name)) as f:
                result = json.load(f)
                self.ram_drive_path = result['ram_drive_path']
                self.libraries = result['libraries']
                self.work_path = result['work_path']
                self.db_file_name = os.path.join(self.work_path, result['db_file_name'])
                self.log_file_name = os.path.join(self.work_path, result['log_file_name'])
                self.log_level = result['log_level']
                self.language_option = result['language_option']
                self.delete_artifacts = bool(result.get('delete_artifacts', 1))
                self.delete_db_on_start = bool(result.get('delete_db_on_start', 0))
                self.clear_ram_drive_on_start = bool(result.get('clear_ram_drive_on_start', 0))
                self.export_path = result['export_path']
                self.use_ram_drive_for_db = result['use_ram_drive_for_db']
                self.ram_drive_db = os.path.join(self.ram_drive_path, 'ram.db') if self.use_ram_drive_for_db else ''
        except Exception as e:
            print(f'Failed to load configuration file: {config_file_name}')
            print(str(e))
            quit(1)
        return


