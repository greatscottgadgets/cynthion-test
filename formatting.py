from colorama import Fore, Back, Style
import colorama

colorama.init()
indent = 0

def msg(text, end, flush=False):
    print(("  " * indent) + "• " + text + Style.RESET_ALL, end=end, flush=flush)

def item(text):
    msg(text, "\n")

def begin(text):
    global indent
    msg(text, ":\n")
    indent += 1

def end():
    global indent
    indent -= 1

def start(text):
    msg(text, "... ", flush=True)

def done():
    print(Fore.GREEN + "OK" + Style.RESET_ALL)

def fail():
    print(Fore.RED + "FAIL" + Style.RESET_ALL)

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
