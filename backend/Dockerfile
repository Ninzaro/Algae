FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app/backend/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md /app/
COPY backend /app/backend

RUN uv pip install --system --no-cache -e ".[dev]"

EXPOSE 8000
CMD ["uvicorn", "alphaforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
