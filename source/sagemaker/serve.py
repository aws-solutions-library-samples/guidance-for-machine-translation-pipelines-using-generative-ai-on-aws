import subprocess
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def start_server():
    # Log SageMaker model path if it exists
    if os.path.exists("/opt/ml/model"):
        logger.info("SageMaker model path found at /opt/ml/model/hub")
        logger.info(f"Model files: {os.listdir('/opt/ml/model/hub')}")
    else:
        logger.info("SageMaker model path not found, will use default paths")
    
    # Start Gunicorn with the application
    gunicorn_command = [
        "gunicorn",
        "--bind", "0.0.0.0:8080",
        "--log-level", "info",
        "--capture-output",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "wsgi:application"
    ]
    
    subprocess.run(gunicorn_command) # nosemgrep

if __name__ == "__main__":
    start_server()
