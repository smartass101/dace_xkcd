#!/bin/sh

if [ $# -ne 1 ] ; then
    echo "Usage: $0 <period in seconds>"
    echo "Deny access to X screen for a given period of time"
    exit 1
else
    slave_inputs_ids=$(xinput list | sed -n 's/.*id=\(.*\)[ \t]*\[slave.*/\1/p')
    for slave_input_id in $slave_inputs_ids ; do
	xinput disable $slave_input_id
    done
    xset dpms force off
    sleep $1
    xset dpms force on
    for slave_input_id in $slave_inputs_ids ; do
	xinput enable $slave_input_id
    done
    exit 0
fi
