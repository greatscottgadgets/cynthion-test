from colorama import Fore, Back, Style
from errors import wrap_exception
import colorama
import state

colorama.init()

def enable_numbering(enable):
    state.numbering = enable

def msg(text, end, flush=False):
    if state.numbering:
        state.step[-1] += 1
        step_text = ".".join(str(s) for s in state.step)
        step_text += " " * (11 - len(step_text))
        prefix = Fore.YELLOW + step_text + Style.RESET_ALL + "│ "
    else:
        prefix = ""
    print(prefix + ("  " * state.indent ) + "• " + text + Style.RESET_ALL, end=end, flush=flush)

def item(text):
    msg(text, "\n")

def todo(text):
    item(Fore.YELLOW + "TODO" + Style.RESET_ALL + ": " + text)

def info(text):
    return Fore.CYAN + str(text) + Style.RESET_ALL

def result(text):
    print(info(text) + ", ", end="")

def ask(text):
    print()
    print(
        Style.BRIGHT +
        Fore.CYAN + " === Please " + text + " and press " +
        Fore.GREEN + "PASS" + Fore.CYAN + " or " +
        Fore.RED + "FAIL" + Fore.CYAN + " === " +
        Style.RESET_ALL)
    print()

def ok(text):
    print()
    print(Fore.GREEN + "PASS" + Style.RESET_ALL + ": " + text)
    print()

def fail(err):
    if state.numbering:
        step_text = err.step + '-'
    else:
        step_text = ''
    print()
    print(Style.BRIGHT + Fore.RED + "FAIL " + Fore.YELLOW + step_text + err.code + Style.RESET_ALL)
    print()
    print(err.msg)
    print()

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
        msg(self.text, "... ", flush=True)
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            print(Fore.GREEN + "OK" + Style.RESET_ALL)
        else:
            print(Fore.RED + "FAIL" + Style.RESET_ALL)
        return False
