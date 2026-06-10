FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_deploy.py .

EXPOSE 8899

CMD ["python", "app_deploy.py"]
