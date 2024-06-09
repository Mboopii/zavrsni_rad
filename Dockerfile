# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
  wget \
  curl \
  gnupg \
  unzip \
  xvfb \
  libxi6 \
  libgconf-2-4 \
  && rm -rf /var/lib/apt/lists/*

# Add Google signing key and install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update \
  && apt-get install -y google-chrome-stable=114.0.5735.198-1 \
  && apt-mark hold google-chrome-stable

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=114.0.5735.90 \
  && wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
  && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
  && rm /tmp/chromedriver.zip

# Set display port to avoid crash
ENV DISPLAY=:99

# Set the working directory
WORKDIR /app

# Copy the application code to the Docker image
COPY . /app

# Copy the API keys
COPY api_keys /app/api_keys

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
