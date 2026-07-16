FROM python:3.12-slim

WORKDIR /app

# Install CPU-only PyTorch + Transformers explicitly, NOT via requirements.txt.
# Two reasons:
#   1. `pip install torch` from PyPI defaults to the CUDA build (~2.5GB of GPU
#      libraries) which is dead weight in a CPU container. The CPU wheel is
#      ~200MB and serves one SMS in ~50-200ms -- inside the <2s target.
#   2. Being explicit here means the image always has what it needs to serve
#      the model, regardless of what requirements.txt happens to list.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir transformers

COPY requirements.txt .
# Strip CR first: on Windows checkouts requirements.txt has CRLF line endings,
# and "^torch$" will NOT match "torch\r" -- pip would then reinstall the CUDA
# wheel over the CPU one. sed normalises, grep drops the lines we handled above.
RUN sed 's/\r$//' requirements.txt | grep -viE '^(torch|transformers)$' > /tmp/reqs.txt \
 && pip install --no-cache-dir -r /tmp/reqs.txt

# Copies app code AND saved_models/ (the trained XLM-RoBERTa model).
# See .dockerignore for what is deliberately excluded (venv, .env, *.db).
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
