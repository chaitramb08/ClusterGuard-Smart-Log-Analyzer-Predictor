FROM python:3.11-slim

WORKDIR /app

# install dependencies first, so Docker caches this layer and only
# reinstalls when requirements.txt actually changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "docker_entrypoint.py"]