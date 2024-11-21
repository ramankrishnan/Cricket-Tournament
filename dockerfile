# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set environment variables to avoid Python buffering and set Flask app
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Set the working directory in the container
WORKDIR /app

# Copy the current project files into the container
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Expose the port that Flask runs on
EXPOSE 5000

# Command to run the Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
