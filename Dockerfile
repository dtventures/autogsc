FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Google Cloud Run typically uses 8080)
EXPOSE 8080

# Environment variables (To be overridden in production)
ENV PORT=8080
ENV OAUTHLIB_INSECURE_TRANSPORT=0 
# Note: In Prod, remove OAUTHLIB_INSECURE_TRANSPORT or set to 0 and use HTTPS

# Command to run the application
# Using gunicorn for production instead of python app.py
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app_oauth:app
