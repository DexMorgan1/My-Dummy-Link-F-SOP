FROM python:3.12-slim

WORKDIR /app

# TgCrypto includes a small native extension. Railway's slim base image does
# not include a compiler or C headers, so install the complete build toolchain
# before pip builds that dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "main.py"]
