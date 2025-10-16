FROM python:3.11-slim

ENV TZ=Asia/Tokyo PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# ランタイムに必要な最低限だけ入れる
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/*

# 依存を先に入れてビルドを速くする
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体をコピー（.dockerignoreで .env や sessions は除外）
COPY . .

# セッション保管場所（あとでホストとマウント）
RUN mkdir -p /app/sessions

# 非rootで動かす（安全）
RUN useradd -m -u 10001 appuser
USER appuser

# コンテナ起動時に実行
CMD ["python", "main.py"]
