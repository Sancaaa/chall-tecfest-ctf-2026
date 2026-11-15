FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /opt/ctf/sequence_data /opt/ctf/secrets && \
    echo "nothing_to_see_here" > /opt/ctf/sequence_data/archive.txt && \
    echo "Public scrolls reside in /opt/ctf/sequence_data/, yet true Beyonder secrets are preserved at /opt/ctf/secrets/lfi_token.txt" > /opt/ctf/sequence_data/scroll_of_truth.txt && \
    echo "BEYONDER ARCHIVE :: lfi_token :: scholar_reading_deep" > /opt/ctf/secrets/lfi_token.txt && \
    chmod 444 /opt/ctf/sequence_data/* /opt/ctf/secrets/*

EXPOSE 5000

CMD ["python", "app.py"]
