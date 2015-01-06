#!/usr/bin/env python2

import os
import re
import select
import logging
import argparse
import subprocess
from ConfigParser import SafeConfigParser

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


_RUNNING_COMMAND = None

def execute_command(command):
    global _RUNNING_COMMAND
    # if hasn't terminated yet
    if _RUNNING_COMMAND is not None and _RUNNING_COMMAND.poll() is None:
            return
    _RUNNING_COMMAND = subprocess.Popen(command.split(' ')) # TODO shlex parse


def check_properties(window_properties, rules):
    for (rules_dict, short_fuse, blacklist, command) in rules:
        matches = []
        for prop, regexp in rules_dict.items():
            try:
                values = window_properties[prop]
            except KeyError:
                matches.append(None)
                continue
            if not isinstance(values, list):
                values = [values]
            for value in values:
                matches.append(regexp.match(value))
        #import pdb; pdb.set_trace()
        if not ((short_fuse and any(matches))
                or (not short_fuse and all(matches))):
            continue            # not enough information
        logger.debug('matches for rules %r: %r' % (rules_dict, matches))
        if blacklist:
            execute_command(command)
        break                   # break for whitelist anyways


def get_rules(config):
    rules = []
    for section in config.sections():
        rules_dict = {name: re.compile(value, re.IGNORECASE) for name, value in
                       config.items(section) if name not in ['short_fuse', 'blacklist', 'command']}
        rules.append((rules_dict, config.getboolean(section,
                                                    'short_fuse'),
                      config.getboolean(section,
                                        'blacklist'),
                      config.get(section, 'command')))
    return rules


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DACE XKCD')
    parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                        help='Configuration file',
                        default=os.path.join(os.path.dirname(
                            os.path.abspath(__file__)), 'dace_xkcd.cfg'),
    )
    parser.add_argument('-d', '--debug', action='store_true')

    args = parser.parse_args()
    config = SafeConfigParser()
    config.optionxform = str    # preserve case
    config.readfp(args.config)
    rules = get_rules(config)

    logger = logging.getLogger(parser.prog)
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(asctime)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.debug('Rules: %r' % rules)

    root_monitor = subprocess.Popen(['xprop', '-spy', '-root',
                                     '_NET_ACTIVE_WINDOW'],
                                    stdout=subprocess.PIPE,
                                )

    active_window_id = get_new_active_window_id(root_monitor)
    active_monitor = create_active_monitor(active_window_id)
    active_window_properties = {}

    while True:          # TODO for a given time interval, e.g. 25 min
        rlist, _, _ = select.select([root_monitor.stdout,
                                     active_monitor.stdout], [], [])
        if root_monitor.stdout in rlist:
            active_window_id = get_new_active_window_id(root_monitor)
            if active_window_id is not None:
                logger.debug('New active window ID %s' % active_window_id)
                active_monitor.terminate()
                active_window_properties.clear()
                active_monitor = create_active_monitor(active_window_id)
        elif active_monitor.stdout in rlist:
            property_name,_ , value = window_property(active_monitor.stdout.readline())
            if property_name is not None:
                logger.debug('New active window PROPERTY %s = %r' % (property_name, value))
                active_window_properties[property_name] = value
                check_properties(active_window_properties, rules)
