import logging
import sys
from inference import app, load_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load model when WSGI starts
logger.info("Initializing model in WSGI...")
try:
    load_model()
    logger.info("Model loaded successfully in WSGI")
except Exception as e:
    logger.error(f"Failed to load model in WSGI: {str(e)}", exc_info=True)
    # Don't raise the exception - allow the application to start anyway

# This is what Gunicorn will import
application = app

# For local testing
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080) # nosec B104s , nosemgrep
