import re
from random import randint, seed

def get_random_num( ):
    # seed random number generator
    seed(1)
    return randint(5, 12)

def parse_active_dates( active_dates ):
    dt_table = { }
    for actdt in active_dates:

        split_sent = actdt.split('@')

        month = split_sent[ 0 ]
        try:
            _ = dt_table[ month ]
        except:
            dt_table[ month ] = ''
        strbuild = split_sent[ 1 ]
        dt_table[ month ] = dt_table[ month ] + strbuild + ' , '

    return dt_table

def sleep_time_conversion( sleeptime ):
    """
    :param sleeptime: INT Number with Unit. It cant be FLOAT
    :return: seconds in INT format
    :examples:
            Input       Output (seconds)
            1m      =   60 * 1
            120m    =   120 * 60
            1h      =   1 * 60
    """
    hr_magic_num = 6
    if not sleeptime:
        return 60 * 60 * hr_magic_num

    mtchs = re.findall('^(\d{1,3})([smh])', sleeptime, re.I)
    if not mtchs:
        return 60 * 60 * hr_magic_num
    try:
        sleep_number = int(mtchs[ 0 ][ 0 ])
    except:
        return 60 * 60 * hr_magic_num

    sleep_unit = mtchs[ 0 ][ 1 ].lower()
    if sleep_unit == 's':
        return sleep_number
    elif sleep_unit == 'm':
        if sleep_number < 361:
            return sleep_number * 60
        else:
            return 60 * 60 * hr_magic_num
    elif sleep_unit == 'h':
        if sleep_number < 7:
            return sleep_number * 60 * 60
        else:
            return 60 * 60 * hr_magic_num
    else:
        return 60 * 60 * hr_magic_num
