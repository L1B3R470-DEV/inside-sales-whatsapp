FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements-router.txt /app/requirements-router.txt
RUN pip install -r /app/requirements-router.txt

COPY router_service.py /app/router_service.py
COPY multi_llm.py /app/multi_llm.py
COPY ai_capacity_registry.py /app/ai_capacity_registry.py
COPY dashboard_sdr.html /app/dashboard_sdr.html
COPY sdr_prompt.txt /app/sdr_prompt.txt

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health', timeout=5)"

CMD ["python", "router_service.py"]
