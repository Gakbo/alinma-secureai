FROM python:3.12-slim

WORKDIR /app

# Install CPU-only PyTorch FIRST, from PyTorch's CPU index.
# Why: `pip install torch` from PyPI defaults to the CUDA build (~2.5GB of
# GPU libraries) which is useless in a container with no GPU. The CPU wheel
# is ~200MB and serves one SMS in ~50-200ms -- well inside the <2s target.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
# torch is already installed above; skip it here so pip doesn't pull the
# CUDA wheel over the top of the CPU one.
RUN grep -v "^torch$" requirements.txt > /tmp/reqs.txt \
    && pip install --no-cache-dir -r /tmp/reqs.txt

# Copies app code AND saved_models/ (the trained model).
# See .dockerignore for what is deliberately excluded (venv, .env, *.db).
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
