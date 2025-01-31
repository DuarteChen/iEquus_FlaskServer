# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/
COPY . /app/
COPY lib/static/images /app/lib/static/images



# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 9090

# Set environment variables (optional)
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Command to run the Flask app
#CMD ["python", "run.py"]
CMD mkdir -p /app/lib/static/images && \
    [ -d "/app/static_backup" ] && cp -r /app/static_backup/* /app/lib/static/images/ || echo "No backup folder found" && \
    python run.py
# Ensure the directory exists and copy images every time the container starts