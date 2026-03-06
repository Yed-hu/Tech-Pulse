# Dockerfile — tells Hugging Face how to build and run your app
# Hugging Face Spaces uses Docker to run any app you want

# Start from official Python 3.11 image
# This is a clean Linux environment with Python pre-installed
FROM python:3.11-slim

# Set the working directory inside the container
# All commands below run from this folder
WORKDIR /app

# Copy requirements first (Docker caches this layer)
# If requirements don't change, Docker skips reinstalling — faster builds
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir = don't store pip cache (keeps image smaller)

# Copy the rest of your project files into the container
COPY . .

# Tell Docker which port the app listens on
# Hugging Face Spaces expects port 7860
EXPOSE 7860

# Command to start the server when container launches
# Uses port 7860 — required by Hugging Face
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]