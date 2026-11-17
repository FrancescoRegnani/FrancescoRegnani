FROM python:3.12-slim
WORKDIR /app
# Solo il codice: segreti e dati restano fuori (vedi .dockerignore).
COPY monitor/ /app/monitor/
COPY context.example.json /app/context.example.json
ENV PYTHONUNBUFFERED=1 HEARTBEAT_FILE=/tmp/heartbeat
RUN useradd --system --uid 10001 --no-create-home monitor
USER monitor
# Sano se l'ultimo ciclo completato risale a meno di 5 minuti.
HEALTHCHECK --interval=60s --timeout=5s --start-period=120s --retries=3 \
  CMD python -c "import os,sys,time; p=os.environ['HEARTBEAT_FILE']; sys.exit(0 if os.path.exists(p) and time.time()-int(open(p).read())<300 else 1)"
CMD ["python", "-m", "monitor", "run"]
