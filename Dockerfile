# Use a specific platform for AMD64 architecture compatibility, as requested.
FROM --platform=linux/amd64 python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Create the input and output directories that will be used for volume mounting
RUN mkdir -p /app/input /app/output

# Copy the dependencies file first to leverage Docker's layer caching.
# This step won't be re-run unless requirements.txt changes.
COPY requirements.txt .

# Install the Python dependencies. The --no-cache-dir flag keeps the image size smaller.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container
COPY process_pdfs.py .

# Set the command to run your script when the container starts.
# This will automatically process the PDFs from the mounted input volume.
CMD ["python", "process_pdfs.py"]