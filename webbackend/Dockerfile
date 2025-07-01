FROM python:3.12-slim

WORKDIR /app

# Install Core Dependencies
COPY requirements.txt core_requirements.txt
RUN pip install -r core_requirements.txt

# Install backend dependencies
COPY webbackend/requirements.txt backend_requirements.txt
RUN pip install -r backend_requirements.txt

COPY webbackend/src/ .
COPY py2c/ py2c/

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
