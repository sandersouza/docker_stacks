#!/bin/bash
duration=300  # 5 minutes in seconds

function run() {
    while true; do
        seq 50 | xargs -P20 -I{} sh -c '
        curl -s -k -o /dev/null \
        -X GET -H "Authorization: Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf" \
        --write-out "%{json}" https://localhost:4433/quizzes/ | ./exporter.py --label curl-http > /dev/null 2>&1
        '
    done
}

function progress_bar() {
    local duration=$1
    local interval=1
    local elapsed=0

    echo -n "Progress: ["
    while [ $elapsed -lt $duration ]; do
        sleep $interval
        echo -n "#"
        elapsed=$((elapsed + interval))
    done
    echo "] Done!"
}

{
    progress_bar $duration &
    progress_pid=$!

    timeout ${duration}s bash -c "$(declare -f run); run"

    kill $progress_pid 2>/dev/null
} 
