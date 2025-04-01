# Use the official Python image as the base for Streamlit
FROM python:3.11-slim

# Install Nginx and apache2-utils (for htpasswd)
RUN apt-get update && apt-get install -y \
    nginx \
    apache2-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Generate .htpasswd file
RUN htpasswd -b -c /etc/nginx/.htpasswd nebula otnebula@007

# Copy the Nginx configuration file
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for Nginx
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost || exit 1

# Run both services using a start script
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]