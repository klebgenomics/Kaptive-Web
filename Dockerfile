FROM python:3.11-slim
WORKDIR /app
COPY scripts /app
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["kaptive-web-serve", "--host", "0.0.0.0"]