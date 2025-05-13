FROM python:3.11-slim

# Install required libs
RUN apt-get update && apt-get install -y gcc git

# Copy files
WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

# Expose port for Flask
EXPOSE 7860

# Run the server
CMD ["python", "run.py"]
