# Use an official slim Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /action

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script and the entrypoint script into the container
COPY dockerhub_cleanup.py .
COPY entrypoint.sh .

# Ensure the entrypoint script is executable
RUN chmod +x entrypoint.sh

# Set the entrypoint to the shell script
ENTRYPOINT ["/action/entrypoint.sh"]
