import sys
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', metavar='[filename]',
                        help='The filename to read from.')
    parser.add_argument('-b', '--beginning', metavar='<beginning_datetime>', type=datetime.fromisoformat,
                        default=datetime.min,
                        help='The date-time to begin parsing from')
    parser.add_argument('-e', '--end', metavar='<end_datetime>', type=datetime.fromisoformat,
                        default=datetime.max,
                        help='The date-time to stop parsing at')
    args = parser.parse_args()

    if args.filename is None:
        print('You must provide a filename to read from')
        sys.exit(-1)

    log_file = open(args.filename, 'r')
    log = log_file.read()

    mcu_check = 'Checking for MCU serial number... '

    failures = {}

    # split test runs by calls to cynthion-test.py
    test_runs = log.split(' cynthion-test.py')
    for t in range(len(test_runs)):
        test = test_runs[t]
        # skip first test
        if t != 0:
            # date strings are 19 characters long and happen right before the cynthion-test.py split
            if test_runs[t-1].startswith('2024',-19):
                test_time = datetime.strptime(test_runs[t-1].split('\n')[-1].strip(), '%Y-%m-%d %H:%M:%S')
            # handling beginning section of gsg8/9 logs with older version of test date output
            else:
                test_time_text = test_runs[t-1].split(' MDT\ncyntest')[0].split('\n')[-1].split(' ')
                if 'PM' in test_time_text:
                    hour = 12+int(test_time_text[-2].split(':')[0])
                year = int(test_time_text[3])
                day = int(test_time_text[1])
                minute = int(test_time_text[-2].split(':')[1])
                second = int(test_time_text[-2].split(':')[2])
                test_time = datetime(year, 4, int(test_time_text[1]), hour, minute, second)
            # pull out the fail code for this test run if there was a failure
            if '\nFAIL' in test:
                code = test.split('\nFAIL ')[1].split('\n')[0]
            elif '\nPASS: All tests completed' in test:
                code = 'PASS'
            else:
                code = None

            if mcu_check in test:
                serial = test.split(mcu_check)[1].split(',')[0]
            else:
                serial = None

            # add each fail code and append each timestamp for which that failure
            # happens and keep track of that count
            if test_time > args.beginning and test_time < args.end:
                if code is not None and code in failures.keys():
                    failures[code][0] += 1
                    if serial not in failures[code][1]:
                        failures[code][1].append(serial)
                elif code is not None:
                    failures[code] = [1, [serial]]


    # sort by number of occurences of each fail code
    sorted_failures = dict(sorted(failures.items(), key=lambda item: item[1][0]))
    print(f"{'FAIL CODE' : <15}{'OCCURENCES' : ^15}{'DEVICE(S)'}")
    print('---------------------------------------------------')
    for fail_code in sorted_failures.keys():
        print(f"{fail_code : <15}{failures[fail_code][0] : ^15}{failures[fail_code][1][:]}")


if __name__ == '__main__':
    main()

