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

# Add Google signing key
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -

# Manually install the specific version of Google Chrome
RUN wget -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
  && dpkg -i /tmp/google-chrome-stable_current_amd64.deb || apt-get -fy install \
  && rm /tmp/google-chrome-stable_current_amd64.deb

# Install ChromeDriver 115
RUN CHROMEDRIVER_VERSION=115.0.5790.102 \
  && wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip \
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
