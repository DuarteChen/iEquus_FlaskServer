FROM python:3.13.3

WORKDIR /app

COPY app.py /app/
COPY lib /app/lib/

COPY requirements.txt .

# Install Python dependencies
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9090

# Command to run your Flask application
CMD ["python", "app.py"]