#!/bin/bash

# Make the script fail on any error
set -e

# Log SageMaker model path if it exists
if [ -d "/opt/ml/model" ]; then
    echo "SageMaker model path exists at /opt/ml/model"
    ls -la /opt/ml/model
fi

# If the command is 'serve', run the serve script
if [ "$1" = "serve" ]; then
    echo "Starting model server with serve command"
    exec python3 serve.py
else
    # Otherwise, run the command as is
    exec "$@"
fi
