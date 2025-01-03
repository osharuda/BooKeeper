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

import subprocess
from typing import *
import os
import fcntl
import re
import glob
import hashlib
import signal

def set_nonblock_io(f):
    flags = fcntl.fcntl(f, fcntl.F_GETFL)
    return fcntl.fcntl(f, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def read_stdout_lines(proc: subprocess.Popen, print_data: False) -> str:
    result = str()
    for line in iter(proc.stdout.readline, b''):
        l = line.rstrip().decode("UTF-8", errors='replace')
        result += l + os.linesep
    if print_data:
        print(result)
    return result

def run_shell_adv(  params : list,
                    cwd=None,
                    input: list = None,
                    print_stdout = True,
                    envvars : dict = None,
                    on_stdout: Callable[[str], None] = None,
                    on_check_kill: Callable[[None], bool] = None,
                    on_started: Callable[[int], None] = None,
                    on_stopped: Callable[[None], None] = None) -> tuple:
    stdout_accum = ""
    env_vars = os.environ.copy()
    if envvars:
        env_vars = {**env_vars, **envvars}
    proc = subprocess.Popen(params,
        cwd=cwd,
        stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
        close_fds=True,
        env=env_vars,
        preexec_fn=os.setpgrp)

    if input:
        data = os.linesep.join(map(str, input))
        ba = data.encode("UTF-8")
        proc.stdin.write(ba)

    proc.stdin.flush()
    proc.stdin.close()

    set_nonblock_io(proc.stdout)

    if on_started:
        on_started(proc.pid)

    while proc.poll() is None:
        s = read_stdout_lines(proc, print_data=print_stdout)
        stdout_accum += s
        if s and on_stdout is not None:
            on_stdout(s)


        if on_check_kill is not None and on_check_kill() is True:
            os.killpg(proc.pid, signal.SIGKILL)

        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass

    s = read_stdout_lines(proc, print_data=print_stdout)
    stdout_accum += s
    if s and on_stdout is not None:
        on_stdout(s)

    if on_stopped:
        on_stopped()

    return (proc.returncode==0, proc.returncode, stdout_accum)


def is_ramdrive_mounted(path: str) -> bool:
    res, code, stdout = run_shell_adv(['mount'], print_stdout=False)
    if not res:
        raise RuntimeError(f'Failed to run mount command: \ncode={code}\n{stdout}')

    pattern = r'^tmpfs\s+on\s+' + path.replace('/', '\\/') + r'.*tmpfs.*$'
    re_exp = re.compile(pattern, re.MULTILINE)
    m = re_exp.search(stdout)
    return bool(m)

def check_djvused_available():
    res, code, stdout = run_shell_adv(['djvused'])
    if res == False:
        raise RuntimeError("djvused doesn't work, install djvulibre-bin package.")

def scan_directory( search_dir: str,
                    scan_param = None,
                    on_file: Callable[[str, Any], Any] = None,
                    on_directory: Callable[[str, Any], Any] = None,
                    on_link: Callable[[str, Any ], Any] = None):
    pattern = os.path.join(search_dir, '**')
    for fn in glob.glob(pattern, recursive=True):
        if on_link and os.path.islink(fn):
            on_link(fn, scan_param)
        elif on_file and os.path.isfile(fn):
            on_file(fn, scan_param)
        elif on_directory and os.path.isdir(fn):
            on_directory(fn, scan_param)
    pass

def get_file_hash(file_name: str) -> hash:
    h = hashlib.md5(open(file_name,'rb').read())
    return h.hexdigest()

def read_text_file(fn: str) -> str:
    with open(fn) as f:
        return f.read()

def split_file_name(file_name: str, known_exts: set[str]=None) -> tuple[str, str]:
    fn = os.path.basename(file_name)
    fnl = len(fn)
    ext = ''
    if known_exts:
        for e in known_exts:
            el = len(e)
            if fnl >= el and fn[fnl-el:]==e:
                ext = fn[fnl-el:]
                fn = fn[:fnl-el]
                break
    else:
        ext = ''
        first_dot = fn.find('.')
        if first_dot >= 0:
            ext = fn[first_dot:]
            fn = fn[0:first_dot]

    return fn, ext

def test_unicode_string(s: str):
    t = s.encode('utf-8', errors='ignore').decode('utf-8')
    return s == t, t
