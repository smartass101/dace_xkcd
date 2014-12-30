import re
import select
import logging
import argparse
import subprocess


window_prop_regexp = re.compile(
    r'(?P<property>.*)\((?P<type>.*)\) = (?P<value>.*)')


def window_property(xprop_line):
    '''Get window properties in the form of a dictionary

    obtained by calling xprop -id *window_id*
    It is line buffered, but that is because the output is read
    from pipe line by line

    Gets only simple assignment properties ( = ) as only they are
    really useful for client matching.
    '''
    match = window_prop_regexp.match(xprop_line)
    if match is None:
        return None, None, None
    property_name, property_type, value = match.groups()
    if '",' in value:
        value = [i.strip(' "') for i in value.strip('{}').split(',')]
    else:
        value = value.strip('"')
    return property_name, property_type, value


def create_active_monitor(window_id):
    active_monitor = subprocess.Popen(['xprop', '-spy', '-id', window_id],
                                    stdout=subprocess.PIPE,
                                )
    return active_monitor


_LAST_WINDOW_ID = None


def get_new_active_window_id(root_monitor):
    global _LAST_WINDOW_ID
    window_id = root_monitor.stdout.readline().split()[-1]
    if window_id == _LAST_WINDOW_ID or window_id == '0x0':
        return None
    _LAST_WINDOW_ID = window_id
    return window_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DACE XKCD')
    args = parser.parse_args()
    logger = logging.getLogger(parser.prog)
    logger.setLevel(logging.DEBUG) # TODO settable
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(asctime)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    root_monitor = subprocess.Popen(['xprop', '-spy', '-root',
                                     '_NET_ACTIVE_WINDOW'],
                                    stdout=subprocess.PIPE,
                                )

    active_window_id = get_new_active_window_id(root_monitor)
    active_monitor = create_active_monitor(active_window_id)

    while True:          # TODO for a given time interval, e.g. 25 min
        rlist, _, _ = select.select([root_monitor.stdout,
                                     active_monitor.stdout], [], [])
        if root_monitor.stdout in rlist:
            active_window_id = get_new_active_window_id(root_monitor)
            if active_window_id is not None:
                logger.debug('New active window ID %s' % active_window_id)
                active_monitor.terminate()
                active_monitor = create_active_monitor(active_window_id)
        elif active_monitor.stdout in rlist:
            property_name,_ , value = window_property(active_monitor.stdout.readline())
            if property_name is not None:
                logger.debug('New active window PROPERTY %s = %r' % (property_name, value))
