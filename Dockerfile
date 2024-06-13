# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Use modified deemix package with fix
COPY local_packages/deemix /app/local_packages/deemix
RUN pip install /app/local_packages/deemix

# Run script.py when the container launches
CMD ["python", "./main.py"]
