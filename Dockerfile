FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV SECRET_KEY=4456131053ffbdf0fca373f0cae1709ada6ddcb05e519933ffec8fa5c513af1c
ENV JWT_SECRET_KEY=0e422654fe2d5764a8ab4308ccccfb9a933e00f1f71cc34094c11558c188eb18
ENV FLASK_ENV=development
ENV PORT=8080

# Gmail SMTP for OTP emails
ENV GMAIL_USER=timetracknotifications@gmail.com
ENV GMAIL_APP_PASSWORD=pnflbstqkbtyufmb

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8080

CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]