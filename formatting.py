from colorama import Fore, Back, Style
from errors import wrap_exception, USBCommsError
import colorama
import state
import os
import re

colorama.init()

if filename := os.environ.get('CYNTHION_TEST_LOG'):
    logfile = open(filename, 'a')
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
else:
    logfile = None

def log(*args, **kwargs):
    kwargs['flush'] = True
    print(*args, **kwargs)
    if logfile is not None:
        print(*(strip(arg) for arg in args), file=logfile, **kwargs)

def strip(text):
    return ansi_escape.sub('', text)

def enable_numbering(enable):
    state.numbering = enable

def msg(text, end):
    if state.numbering:
        state.step[-1] += 1
        step_text = ".".join(str(s) for s in state.step)
        step_text += " " * (11 - len(step_text))
        prefix = Fore.YELLOW + step_text + Style.RESET_ALL + "│ "
    else:
        prefix = ""
    log(prefix + ("  " * state.indent ) + "• " + text + Style.RESET_ALL, end=end)

def item(text):
    msg(text, "\n")

def todo(text):
    item(Fore.YELLOW + "TODO" + Style.RESET_ALL + ": " + text)

def info(text):
    return Fore.CYAN + str(text) + Style.RESET_ALL

def result(text):
    log(info(text) + ", ", end="")

def ask(text):
    log()
    log(
        Style.BRIGHT +
        Fore.CYAN + " === Please " + text + " and press " +
        Fore.GREEN + "PASS" + Fore.CYAN + " or " +
        Fore.RED + "FAIL" + Fore.CYAN + " === " +
        Style.RESET_ALL)
    log()

def ok(text):
    log()
    log(Fore.GREEN + "PASS" + Style.RESET_ALL + ": " + text)
    log()

def fail(err):
    if state.numbering:
        step_text = err.step + '-'
    else:
        step_text = ''
    log()
    log(Style.BRIGHT + Fore.RED + "FAIL " + Fore.YELLOW + step_text + err.code + Style.RESET_ALL)
    log()
    log(err.msg)
    log()
    if isinstance(err, USBCommsError):
        logfile = '/var/log/kern.log'
        prefix = 'kernel: '
        count = 10
        try:
            log_lines = open(logfile, 'r').readlines()
            log(f"Last {count} lines of {logfile}:\n")
            for line in log_lines[-count:]:
                start = line.find(prefix) + len(prefix)
                log(line.rstrip()[start:])
        except IOError as e:
            log(f"Failed to read {logfile}: {e.strerror}")
        log()

class group():
    def __init__(self, text):
        self.text = text
    def __enter__(self):
        msg(self.text, ":\n")
        state.indent += 1
        state.step.append(0)
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        # If we got an exception, wrap it into a CynthionTestError now,
        # before we lose the step information.
        if exc_value is not None:
            wrap_exception(exc_value)
        state.step.pop()
        state.indent -= 1
        return False

class task():
    def __init__(self, text):
        self.text = text
    def __enter__(self):
        msg(self.text, "... ")
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            log(Fore.GREEN + "OK" + Style.RESET_ALL)
        else:
            log(Fore.RED + "FAIL" + Style.RESET_ALL)
        return False
