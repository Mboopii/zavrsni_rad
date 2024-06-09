# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Set display port to avoid crash
ENV DISPLAY=:99
ENV PORT=5000

# Copy the application code to the Docker image
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose the port the app runs on
EXPOSE 5000

# Run the application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers=4", "--threads=2"]