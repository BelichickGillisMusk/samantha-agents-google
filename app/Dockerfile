FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Install deps first (better layer caching).
COPY app/requirements.txt /srv/app/requirements.txt
RUN pip install -r /srv/app/requirements.txt

# Copy app + the persona files chat.py reads at runtime.
COPY app/        /srv/app/
COPY projects/   /srv/projects/

EXPOSE 8080
# Cloud Run sets $PORT; respect it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
