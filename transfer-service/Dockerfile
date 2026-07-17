# FROM python:3.11-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# EXPOSE 5002

# CMD ["python", "app.py"]


FROM python:3.11-slim AS builder

# Build-time only: needed in case any dependency has to compile from source
# (e.g. psycopg2-binary falling back to building instead of using a wheel).
# None of this ends up in the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user --only-binary :all: -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Copy only the installed Python packages from the builder stage,
# not the compiler or build tools used to create them.
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 5002

CMD ["python", "app.py"]
