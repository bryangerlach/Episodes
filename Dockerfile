# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Define environment variable for Django settings module
ENV PYTHONUNBUFFERED 1

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]