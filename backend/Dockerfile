FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Run `alembic upgrade head` as its own deploy step before starting this
# container (see DEPLOYMENT_PLAN.md's "Migrations as part of deploy") —
# not baked into this CMD, since that would re-run on every replica start
# under more than one instance.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
