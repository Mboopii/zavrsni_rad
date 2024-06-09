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

# Install ChromeDriver 125
RUN CHROMEDRIVER_VERSION=125.0.6422.141 \
  && wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip \
  && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
  && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
  && chmod +x /usr/local/bin/chromedriver \
  && rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64

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
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers=2", "--threads=2"]