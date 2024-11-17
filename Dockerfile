FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt mail-monitor.py supervisord.conf ./

# Install and configure supervisord and pip requirements
RUN apt-get update \
    && apt-get install -y supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt \
    && mv supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Start supervisord when the container launches
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]