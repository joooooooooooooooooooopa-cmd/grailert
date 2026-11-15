FROM python:3.12-slim
WORKDIR /app
COPY server.py poster.py ./
COPY static/ ./static/
ENV PORT=3000
CMD ["python", "-u", "server.py"]
