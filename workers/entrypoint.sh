#!/bin/bash
set -e

wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    while ! redis-cli -h redis ping > /dev/null 2>&1; do
        echo "Redis is not ready yet. Waiting..."
        sleep 2
    done
    echo "Redis is ready!"
}

wait_for_zero_secrets() {
    echo "Waiting for Zero secrets to be available..."
    if [ -z "$ZERO_TOKEN" ]; then
        echo "ERROR: ZERO_TOKEN environment variable is required"
        exit 1
    fi
    echo "Zero token is available"
}

# Function to start email workers
start_email_workers() {
    echo "Starting email workers..."
    python start_email_workers.py
}

# Function to start worker monitor (Flower)
start_worker_monitor() {
    echo "Starting worker monitor (Flower)..."
    python start_email_workers.py --monitor
}

# Main execution
main() {
    echo "Starting Evently Workers Container..."
    
    wait_for_zero_secrets
    wait_for_redis
    
    if [ "$1" = "--monitor" ]; then
        start_worker_monitor
    else
        start_email_workers
    fi
}

main "$@"