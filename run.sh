#!/bin/bash

# Number of simultaneous executions
device_list="sm02 sm05"
mypassword=`cat password.txt`

# Loop to start multiple instances
for i in $device_list; do
    echo "Starting dev $i..."
    echo "$mypassword" | sudo -S python3 runner.py -d "$i" &
done

# Wait for all background processes to complete
wait

echo "All processes have completed."
