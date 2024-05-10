FROM python:3.10.9-slim

WORKDIR /usr/src/app
# COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN adduser --system --shell /bin/bash nonroot && \
    pip install --no-cache-dir --upgrade poetry wheel pysu 
    # && \
    # chmod +rx /usr/local/bin/docker-entrypoint.sh

USER nonroot

COPY . .

RUN poetry install --no-cache --no-root --without dev --with postgres

# USER root
# ENTRYPOINT [ "/usr/local/bin/docker-entrypoint.sh" ]
CMD poetry run aerich upgrade && poetry run python3 ./src/main.py
