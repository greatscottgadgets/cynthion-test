from colorama import Fore, Back, Style
import colorama

colorama.init()
indent = 0

def msg(text, end, flush=False):
    print(("  " * indent) + "• " + text + Style.RESET_ALL, end=end, flush=flush)

def item(text):
    msg(text, "\n")

def todo(text):
    item(Fore.YELLOW + "TODO" + Style.RESET_ALL + ": " + text)

def info(text):
    return Fore.CYAN + str(text) + Style.RESET_ALL

def ask(text):
    print()
    print(
        Fore.BLUE + " === Please " + text + " and press " +
        Fore.GREEN + "PASS" + Fore.BLUE + " or " +
        Fore.RED + "FAIL" + Fore.BLUE + " === " +
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
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        global indent
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
