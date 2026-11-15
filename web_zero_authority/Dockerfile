FROM python:3.12-slim

WORKDIR /app

RUN useradd -r -s /bin/false ctf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY init_db.py run.py schema.sql ./

RUN python init_db.py && chown -R ctf:ctf /app

USER ctf

EXPOSE 50201

CMD ["gunicorn", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:50201", "run:app"]
