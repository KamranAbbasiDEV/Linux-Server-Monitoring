FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir . && useradd -r -u 10001 -m monitor
USER monitor
# Docker deliberately runs the SYNTHETIC demo: container metrics are not host metrics.
CMD ["linuxops", "demo"]
