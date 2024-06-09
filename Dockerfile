# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
  wget \
  curl \
  gnupg \
  unzip

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy the application code to the Docker image
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]
