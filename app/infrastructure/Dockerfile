FROM python:3.12-slim
WORKDIR /srv/app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
RUN useradd --create-home saferoute && chown -R saferoute:saferoute /srv/app
USER saferoute
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
