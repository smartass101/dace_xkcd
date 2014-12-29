import re
import argparse
import logging
import subprocess


window_prop_regexp = re.compile(
    r'(?P<property>.*)\((?P<type>.*)\)(?P<relation>:| = )(?P<value>.*)')


def window_properties(window_id):
    '''Get window properties in the form of a dictionary

    obtained by calling xprop -id *window_id*
    '''
    output = subprocess.check_output(['xprop', '-id', window_id])
    properties = {}
    properties_types = {}
    rel = None
    compound_value = None
    
    for line in output.splitlines():
        match = window_prop_regexp.match(line)
        if match is None:
            if rel == ':':
                compound_value.append(line.strip())
        else:
            prop, prop_type, rel, value = match.groups()
            properties_types[prop] = prop_type
            if rel == ':':
                compound_value = []
                properties[prop] = compound_value
                if value:
                    compound_value.append(value)
                continue
            if '",' in value:
                value = [i.strip(' "') for i in value.strip('{}').split(',')]
            else:
                value = value.strip('"')
            properties[prop] = value
    return properties, properties_types

    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DACE XKCD')
    args = parser.parse_args()
    logger = logging.getLogger(parser.prog)
    logger.setLevel(logging.DEBUG) # TODO settable
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(asctime)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    monitor = subprocess.Popen(['xprop', '-spy', '-root',
                                '_NET_ACTIVE_WINDOW'],
                               stdout=subprocess.PIPE,
                           )

    last_window_id = None
    while True:                 # TODO for some max duration, e.g. 25 min
        window_id = monitor.stdout.readline().split()[-1]
        if window_id == last_window_id:
            continue
        last_window_id = window_id
        logger.debug('New focused window id %s' % window_id)
        logger.debug('Focused window properties: %r\ntypes: %r' % window_properties(window_id))
