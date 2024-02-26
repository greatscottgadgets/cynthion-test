from tests import *

def check():
    # Set up test system.
    setup()

if __name__ == "__main__":
    try:
        check()
        ok("Self-check complete")
    except KeyboardInterrupt:
        fail("Self-check stopped by user")
    except Exception as e:
        fail(str(e))
    reset()
