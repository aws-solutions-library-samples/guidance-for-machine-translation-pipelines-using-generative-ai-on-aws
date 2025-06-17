import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Gunicorn config variables
loglevel = "INFO"
workers = 1
bind = "0.0.0.0:8080"
worker_class = "sync"
keepalive = 120

# Access log - records incoming HTTP requests
accesslog = "-"  # "-" means log to stdout
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Error log - records Gunicorn server goings-on
errorlog = "-"  # "-" means log to stderr

# Whether to send Flask output to the error log 
capture_output = True

# Initialize logger for the Flask application
def on_starting(server):
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    file_handler = RotatingFileHandler(
        'model_server.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
