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

import signal
from logger import Logger

class Terminator(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Terminator, cls).__new__(cls)
            cls._instance.exit_requested = None
            cls._instance.initialize()
        return cls._instance

    def __del__(self):
        signal.signal(signal.SIGINT, self.old_handler)
        self.logger.print_diagnostic('Terminator destroyed.', console_only=True)

    @staticmethod
    def terminator_signal_handler(sig, frame):
        t = Terminator()
        t.set_signal()

    def set_signal(self):
        self.exit_requested = True

    def initialize(self):
        self.logger = Logger()
        self.exit_requested = False
        self.old_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, Terminator.terminator_signal_handler)
        self.logger.print_diagnostic('Terminator created.', console_only=True)

    def check_exit(self):
        while self.exit_requested:
            reply = input('Are you sure to exit? [Y/N] : ')
            if reply.lower() == 'y':
                self.logger.print_log('Program terminated due to user request. Bye!')
                quit(0)
            elif reply.lower() == 'n':
                self.exit_requested = False
