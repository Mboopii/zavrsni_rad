# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Copy the application code to the Docker image
COPY . /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Set environment variables
ENV SELENIUM_URL=http://selenium:4444/wd/hub

# Run the application
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers=2", "--threads=2"]
