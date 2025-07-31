FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y gcc libpq-dev curl unzip \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libffi-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright==1.44.0
RUN python -m playwright install --with-deps

WORKDIR /bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/bot/..

CMD ["python", "bot.py"]
