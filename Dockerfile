# Self-hosted GPU Cloud Compare: one container, no external CI. nginx
# serves the static Astro build; docker/entrypoint.sh re-syncs prices and
# rebuilds in place on a schedule (default every 6h — see
# SYNC_INTERVAL_HOURS in docker-compose.yaml). See README.md's "Self-hosting
# with Docker" section for the full picture.
FROM node:20-alpine

# bash: entrypoint.sh readability. nginx: serves the built dist/.
# python3/py3-pip: scripts/fetch-prices.ts shells out to
# scripts/gpuhunt/fetch_gpuhunt.py (github.com/dstackai/gpuhunt, MPL-2.0)
# for the CloudRift/JarvisLabs live fetchers — see README.md's "Live price
# sync" section for why. Every other fetcher is pure Node `fetch`, so this
# is the only reason Python ends up in the image at all.
RUN apk add --no-cache bash nginx python3 py3-pip

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Isolated venv, not a system-wide pip install — Alpine's python3 is
# "externally managed" (PEP 668) and refuses a bare `pip install`.
# GPUHUNT_PYTHON_BIN tells fetch-prices.ts to use this interpreter instead
# of guessing `python3` off PATH (see scripts/fetch-prices.ts).
RUN python3 -m venv /opt/gpuhunt-venv \
  && /opt/gpuhunt-venv/bin/pip install --no-cache-dir -r scripts/gpuhunt/requirements.txt
ENV GPUHUNT_PYTHON_BIN=/opt/gpuhunt-venv/bin/python3

# Bake a first snapshot into the image so `docker run` has something to
# serve immediately, before the runtime sync loop has fired even once.
# This is the only build that runs `astro check` — a broken build fails
# `docker build`, not a container that's already live.
RUN npm run build

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV SYNC_INTERVAL_HOURS=6
EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
