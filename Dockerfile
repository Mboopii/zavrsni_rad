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

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update \
  && apt-get install -y google-chrome-stable

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
  && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
  && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
  && rm /tmp/chromedriver.zip

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy the application code to the Docker image
COPY . /app
WORKDIR /app

# Copy the API keys
COPY api_keys /app/api_keys

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the application
CMD ["python", "app.py"]
