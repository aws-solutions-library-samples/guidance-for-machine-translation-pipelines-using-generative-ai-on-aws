# checkov:skip=CKV_DOCKER_3
# checkov:skip=CKV_DOCKER_2
FROM pytorch/pytorch:2.6.0-cuda11.8-cudnn9-runtime

RUN apt-get update && rm -rf /var/lib/apt/lists/* && apt-get clean
# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Set working directory
WORKDIR /app

# Copy application files
COPY inference.py wsgi.py serve.py /app/

# Copy and set up the entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Make port 8080 available
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV GUNICORN_CMD_ARGS="--capture-output --enable-stdio-inheritance"

# Set the entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (will be overridden by 'serve' in SageMaker)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--log-level", "info", "--capture-output", "--access-logfile", "-", "--error-logfile", "-", "wsgi:application"]
