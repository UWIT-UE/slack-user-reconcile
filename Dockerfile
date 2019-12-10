
FROM python:3.7-slim

ENV PATH="/venv/bin:$PATH"
RUN python3 -m venv /venv

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY user-reconcile.py /app/user-reconcile.py

ENTRYPOINT [ "python", "/app/user-reconcile.py" ]

