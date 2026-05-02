

# Stage 1: build the frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build


# Stage 2: Python API + built frontend
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/agent/      ./agent/
COPY backend/api/        ./api/
COPY backend/ingestion/  ./ingestion/
COPY backend/utils/      ./utils/
COPY backend/data/       ./data/

COPY --from=frontend-builder /frontend/dist /app/frontend/dist

ENV PYTHONPATH=/app

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
