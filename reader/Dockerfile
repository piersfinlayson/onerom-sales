FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
VOLUME /data
RUN adduser --disabled-password --gecos '' --uid 10000 appuser
USER appuser
CMD ["python", "app.py"]