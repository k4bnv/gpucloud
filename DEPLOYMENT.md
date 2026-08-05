# Deployment Guide

Two independent ways to run this site. Pick one — you don't need both.

| | **A. Self-hosted Docker** | **B. Static host (Cloudflare Pages / Vercel / Netlify)** |
|---|---|---|
| Where it runs | Your own server (e.g. a homelab LXC/VM) | A managed static host |
| Price freshness | Container re-syncs + rebuilds itself every `SYNC_INTERVAL_HOURS` | GitHub Action commits fresh prices to `main`; host auto-deploys on push |
| Needs | Docker + Docker Compose | A GitHub connection to the host, nothing self-hosted |
| TLS / domain | You point something at it (Cloudflare Tunnel, reverse proxy, etc.) | Host handles TLS + domain natively |

---

## Environment variables (both paths)

Copy [`.env.example`](.env.example) → `.env` and fill in what you need. Every variable is optional — anything left unset falls back to a safe default, nothing breaks if you only set some of these. All of them are read at **build time** and baked into the static HTML; there's no runtime lookup in the browser.

| Variable | Default if unset | Purpose |
|---|---|---|
| `SITE_URL` | `https://gpucompare.cloud` | Domain baked into `sitemap.xml`, every `<link rel="canonical">`, and OG/Twitter tags. Only set this if deploying to a different domain. |
| `AFFILIATE_URL_RUNPOD` | `https://runpod.io/?ref=AFFILIATE_ID` (placeholder) | Real RunPod referral link. |
| `AFFILIATE_URL_VAST_AI` | `https://vast.ai/?ref=AFFILIATE_ID` (placeholder) | Real Vast.ai referral link. |
| `AFFILIATE_URL_HYPERSTACK` | `https://console.hyperstack.cloud/?ref=AFFILIATE_ID` (placeholder) | Real Hyperstack referral link. |
| `AFFILIATE_URL_PAPERSPACE` | `https://www.paperspace.com/?ref=AFFILIATE_ID` (placeholder) | Real Paperspace referral link. |
| `AFFILIATE_URL_NOVITA_AI` | `https://novita.ai/?ref=AFFILIATE_ID` (placeholder) | Real Novita AI referral link. |
| `AFFILIATE_URL_THUNDER_COMPUTE` | `https://www.thundercompute.com/?ref=AFFILIATE_ID` (placeholder) | Real Thunder Compute referral link. |
| `RUNPOD_API_KEY` | unset → RunPod fetcher no-ops (not an error) | Enables the live RunPod price fetcher in `scripts/fetch-prices.ts`. Get one from the RunPod dashboard. |
| `HYPERSTACK_API_KEY` | unset → Hyperstack fetcher no-ops (not an error) | Enables the live Hyperstack price fetcher (`/core/flavors` + `/pricebook`). Get one from the Hyperstack console. |
| `THUNDER_API_KEY` | unset → Thunder Compute fetcher no-ops (not an error) | Enables the live Thunder Compute price fetcher (`/v2/pricing` + `/v2/specs`). Get one from the Thunder Compute dashboard. |
| `SOCIAL_URLS` | unset → `sameAs` omitted from schema | Comma-separated list of your own real off-site profile URLs (LinkedIn company page, GitHub org, etc.) — becomes `sameAs` in the sitewide Organization JSON-LD (`src/lib/schema.ts`). Only put URLs you actually own; never a placeholder. |
| `SYNC_INTERVAL_HOURS` | `6` | **Docker only.** Hours between in-container price re-syncs. Set directly in `docker-compose.yaml`, not `.env`. |
| `DEPLOY_HOOK_URL` | unset → step skipped | **GitHub Actions only**, set as a repo *secret* (Settings → Secrets → Actions), not in `.env`. POSTed after a price commit — only needed if your static host doesn't auto-deploy on git push. |

The `AFFILIATE_URL_<SLUG>` convention: provider `slug` from `src/data/providers.json`, uppercased, hyphens → underscores (`vast-ai` → `AFFILIATE_URL_VAST_AI`). Adding a new provider to `providers.json` later gets its own `AFFILIATE_URL_<NEW_SLUG>` automatically — no code change needed, see `src/lib/data.ts`.

---

## A. Self-hosted Docker

```bash
git clone https://github.com/k4bnv/gpucloud.git
cd gpucloud
cp .env.example .env
nano .env                          # fill in real affiliate links, SITE_URL if different
docker network create frontend 2>/dev/null || true   # only if it doesn't already exist
docker compose up -d --build
```

Container serves on port **8090** (`http://<host>:8090`) and:
1. Runs `npm run sync-prices` + rebuilds the site once on start.
2. Repeats that every `SYNC_INTERVAL_HOURS` (default 6) for the life of the container — see `docker/entrypoint.sh`. A failed sync/build leaves the currently-served site untouched; it never takes the site down.

**Update the code later** (new features, catalog changes — not prices, those refresh themselves):
```bash
cd gpucloud
git pull
docker compose up -d --build
```

### Putting a domain in front of it

`docker-compose.yaml` only publishes plain HTTP on 8090 — nothing here terminates TLS. Point your own reverse proxy / tunnel at `http://<host>:8090` (or `http://gpu-cloud-compare:80` if it's reachable on the same Docker network). A **Cloudflare Tunnel** is a good fit if you don't want to open any ports: add a Public Hostname in your tunnel pointing your domain at that address, Cloudflare terminates TLS at its edge, no port-forwarding needed on your side.

---

## B. Static host (Cloudflare Pages / Vercel / Netlify)

Build settings (same for any of the three):

| Setting | Value |
|---|---|
| Build command | `npm run build` |
| Output directory | `dist` |
| Node version | `20` (from `.nvmrc`) |

Set the environment variables from the table above in the host's project settings UI. Connect the host's git integration to `main` on this repo so it redeploys on every push.

### Keeping prices fresh on this path

`.github/workflows/daily-sync.yml` runs every 6 hours (or on-demand via **Actions → GPU Price Sync → Run workflow**), re-syncs prices, and commits to `main` if anything changed. If your host auto-deploys on push (the default for all three), that commit alone triggers a fresh deploy — `DEPLOY_HOOK_URL` isn't needed. Set it as a repo secret only if you disabled git-based auto-deploy and need an explicit trigger.

Optional repo secrets: `RUNPOD_API_KEY` (Settings → Secrets and variables → Actions) — same purpose as the `.env` var above, but for the CI job specifically; independent of what's set in `.env`.

---

## After deploying: get it into Google

The site ships `sitemap.xml` / `robots.txt` / canonical tags already correct — nothing else to configure in code.

1. **Google Search Console** (search.google.com/search-console) → Add property → **Domain** → your domain.
2. Verify via DNS TXT record (trivial if the domain is on Cloudflare: Dashboard → DNS → add the `google-site-verification=...` TXT record Google gives you).
3. **Sitemaps** → submit `sitemap-index.xml`.
4. **URL Inspection** → your homepage URL → **Test Live URL** — confirms Googlebot can actually fetch the page right now. If this fails on a Cloudflare-fronted domain, check **Security → Bots → Bot Fight Mode** is OFF and Security Level isn't "I'm Under Attack" — these block Googlebot along with everything else.
5. Give it time — a submitted sitemap can take from an hour to a day to show a real "discovered URLs" count even on a fully working site.
