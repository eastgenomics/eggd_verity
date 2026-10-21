#######  Builder Stage 
FROM python:3.12-alpine as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install OS-level build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers graphviz-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

####### Final Stage
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8050

# Activate the virtual environment and run the application
ENV PATH="/opt/venv/bin:$PATH"
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8050", "app.main:server"]