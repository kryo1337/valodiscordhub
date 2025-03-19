FROM python:3.9-slim

WORKDIR /db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "init_db.py"]
