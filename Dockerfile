FROM python:3.10-slim

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .  
# main.py, cogs, db.py, data/gacha_data.csvなど全てコピー
# data/gacha_data.csvもビルドコンテキスト内に存在

CMD ["python", "main.py"]
