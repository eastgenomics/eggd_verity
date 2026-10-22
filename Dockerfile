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

# The SQLite database is mounted at runtime, not baked into the image:
#   docker run -v /path/to/db_dir:/db ...
# Override with VERITY_DB_PATH or use Postgres via VERITY_DATABASE_URL.
ENV VERITY_DB_PATH=/db/verity_db.sqlite3
RUN mkdir -p /db

# Copy the application code (the database is excluded via .dockerignore)
COPY . .

# Expose the port the app runs on
EXPOSE 8050

# Activate the virtual environment and run the application
ENV PATH="/opt/venv/bin:$PATH"
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8050", "app.main:server"]