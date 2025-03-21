# Use an official Python image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script
COPY bot.py .

# Expose the Flask port
EXPOSE 5000

# Set environment variables (use this if using Koyeb environment settings)
ENV BOT_TOKEN=${BOT_TOKEN}

# Run the bot and Flask server
CMD ["python", "bot.py"]
