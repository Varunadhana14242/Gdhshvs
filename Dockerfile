# Use official Python image
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script
COPY bot.py .

# Expose the Flask port
EXPOSE 5000

# Run the bot and Flask server
CMD ["gunicorn", "-b", "0.0.0.0:5000", "bot:app"]
