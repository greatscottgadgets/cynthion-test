from colorama import Fore, Back, Style
import colorama

colorama.init()
indent = 0
numbering = False

step = [0]

def enable_numbering():
    global numbering
    numbering = True

def msg(text, end, flush=False):
    if numbering:
        step[-1] += 1
        step_text = ".".join(str(s) for s in step)
        step_text += " " * (11 - len(step_text))
        prefix = Fore.YELLOW + step_text + Style.RESET_ALL + "│ "
    else:
        prefix = ""
    print(prefix + ("  " * indent ) + "• " + text + Style.RESET_ALL, end=end, flush=flush)

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

def fail(text):
    print()
    print(Fore.RED + "FAIL" + Style.RESET_ALL + ": " + text)
    print()

class group():
    def __init__(self, text):
        self.text = text
    def __enter__(self):
        global indent
        msg(self.text, ":\n")
        indent += 1
        step.append(0)
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        global indent
        step.pop()
        indent -= 1
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
