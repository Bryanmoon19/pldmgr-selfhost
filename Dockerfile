FROM python:3.12-alpine

WORKDIR /app
COPY repo_server.py .

# Drop-folder is a volume; create so permissions are predictable
RUN mkdir -p /app/payloads

EXPOSE 8090
CMD ["python", "repo_server.py", "8090"]