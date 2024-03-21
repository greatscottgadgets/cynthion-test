from tests import *

def check():
    # Set up test system.
    setup()

if __name__ == "__main__":
    try:
        with error_conversion():
            check()
            ok("Self-check complete")
    except CynthionTestError as error:
        fail(error)
    reset()
