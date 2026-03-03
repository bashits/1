FROM python:3.12-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

# Install poetry
RUN pip install poetry

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /data/clips/source /data/clips/processed /data/clips/thumbnails \
    /data/montage/output /data/montage/temp /data/montage/assets/sfx /data/montage/assets/music

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
