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
from enum import IntEnum
from termcolor import colored


class LoggerLevel(IntEnum):
    Diagnostic = 0
    Log        = 1
    Warning    = 2
    Error      = 3

    @classmethod
    def list(cls):
        return list(map(lambda c: c.name, cls))


class Logger(object):
    _instance = None


    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.log_file = None
            cls._instance.initialize(kwargs['log_file'], kwargs['level'])
        return cls._instance

    def __del__(self):
        self.print_diagnostic('Logger destroyed.', console_only=True)


    def initialize(self, log_file: str, level):
        if type(level) == LoggerLevel:
            self.level = level
        elif type(level) == str:
            lcase_level = level.lower()
            for ev in LoggerLevel.list():
                if ev.lower() == lcase_level:
                    self.level = LoggerLevel[ev]
                    break
            if self.level is None:
                raise RuntimeError(f'Failed to parse logger level: {level}')
        elif type(level) == int:
            self.level = LoggerLevel(level)

        self.log_file = log_file

        if os.path.isfile(log_file):
            os.unlink(log_file)
        self.print_diagnostic(f'Logger created. Log file: {log_file}', console_only=True)


    def write_log(self, s, linesep=os.linesep):
        with open(self.log_file, "a") as f:
            f.write(s + linesep)


    def print_diagnostic(self, s, console_only=False, options=None, linesep=os.linesep):
        if options is None:
            options = ('dark_grey',)

        if self.level <= LoggerLevel.Diagnostic:
            print(colored(s, *options), end=linesep)
            if not console_only and self.log_file:
                self.write_log(s, linesep=linesep)


    def print_log(self, s, console_only=False, options=None, linesep=os.linesep):
        if options is None:
            options = ('white',)

        if self.level <= LoggerLevel.Log:
            print(colored(s, *options), end=linesep)
            if not console_only and self.log_file:
                self.write_log(s, linesep=linesep)


    def print_warn(self, s, console_only=False, options=None, linesep=os.linesep):
        if options is None:
            options = ('black', 'on_yellow')

        if self.level <= LoggerLevel.Warning:
            print(colored(s, *options), end=linesep)
            if not console_only and self.log_file:
                self.write_log(s, linesep=linesep)


    def print_err(self, s, console_only=False, options=None, linesep=os.linesep):
        if options is None:
            options = ('red', )

        if self.level <= LoggerLevel.Error:
            print(colored(s, *options), end=linesep)
            if not console_only and self.log_file:
                self.write_log(s, linesep=linesep)
