# GPUCompare.cloud

Programmatic-SEO price comparison site for GPU cloud rental (RunPod, Vast.ai,
Hyperstack, Paperspace, Novita AI, Thunder Compute, CloudRift, JarvisLabs,
Hot Aisle). Astro + React islands + Tailwind, fully static (SSG), built for
speed, mobile-first layout and affiliate-link conversion.

> **Deploying this?** See [DEPLOYMENT.md](DEPLOYMENT.md) for the full
> guide — environment variables, self-hosted Docker, static-host CI, and
> getting the site into Google.

## Stack

- **Framework:** [Astro](https://astro.build) (static output) + React islands
  for the interactive parts only (filter table, breadcrumbs stay zero-JS)
- **Styling:** Tailwind CSS, dark-mode-by-default, neon green/blue accents
- **Icons:** [lucide-react](https://lucide.dev)
- **UI primitives:** hand-rolled shadcn-style components (`src/components/ui`)
- **Data:** static JSON fixtures in `src/data/`, no database, no API calls at
  request time — everything is resolved at build time for SSG

## Data model

| File | Shape | Purpose |
|---|---|---|
| `src/data/gpus.json` | `GPU[]` | GPU specs (VRAM, architecture, target tasks) |
| `src/data/providers.json` | `Provider[]` | One row per (provider, GPU) rental offer |
| `src/data/use-cases.json` | `UseCase[]` | Task bundles that drive `/best-gpu-for/*` |

Types live in `src/types/index.ts`. `src/lib/data.ts` is the only place that
reads the JSON files and joins them (`getAllComputedOffers`,
`getComputedOffersForGpu`, …) — pages never touch the JSON directly.

**Ratings and review counts are still placeholder test data.** Pricing
(`price_on_demand`, `price_spot`) is kept live by `npm run sync-prices` —
see below. Affiliate URLs default to a `?ref=AFFILIATE_ID` placeholder but
are meant to be overridden via environment variables, not hand-edited in
the JSON — see **[Affiliate links](#affiliate-links)**.

**Provider price freshness varies by source.** Hyperstack, Thunder Compute,
CloudRift, JarvisLabs and Hot Aisle now have real live fetchers (see the
fetcher table below) — set their API keys (CloudRift needs none) and their
rows self-correct on every sync, same as RunPod/Vast.ai. Paperspace and Novita AI
don't have a fetcher yet: Novita AI's committed rows were cross-checked
against gpus.io's live aggregator at the time they were added but won't
self-correct after that; Paperspace's rows are a rough ballpark estimate,
not verified against its own pricing page. Re-verify both periodically
before relying on them for real traffic.

**Why not just scrape a price-comparison aggregator (gpus.io,
gputracker.dev, GetDeploying...) for everything?** Their Terms of Service
explicitly forbid feeding their aggregated data into a competing
comparison product — that's not a technicality, it's their whole business
model. Every fetcher here instead talks to a GPU cloud's own first-party
API, or (for CloudRift/JarvisLabs) goes through `gpuhunt`
(github.com/dstackai/gpuhunt, MPL-2.0), a genuinely open-source library
that itself calls those same first-party APIs — not an aggregator.

## Routes

| Route | Generation | Purpose |
|---|---|---|
| `/` | static | Filterable/sortable comparison table of every GPU |
| `/gpu/[slug]/` | `getStaticPaths` over `gpus.json` | Per-GPU provider comparison, cost calculator + FAQ (Product/AggregateRating/FAQPage schema) |
| `/compare/[a]-vs-[b]/` | `getStaticPaths` over comparable GPU pairs + all provider pairs (`src/utils/pseo.ts`) | AI Verdict, side-by-side spec table, pros/cons, cost efficiency, FAQ |
| `/compare/` | static | Hub page linking every generated comparison |
| `/best-gpu-for/[use-case]/` | `getStaticPaths` over `use-cases.json` | Ranked GPU picks for a task (LLM training, ComfyUI, …) |
| `/robots.txt` | endpoint | Points crawlers at the sitemap |
| `/sitemap-index.xml` | `@astrojs/sitemap` | Auto-generated at build time |

## Programmatic comparisons (`/compare/`)

`src/utils/pseo.ts` is the single source of truth for what `/compare/`
pages exist:

- `generateGpuPairs()` — every GPU pair worth comparing (`areGpusComparable`
  filters to same-vendor cards within a ~4x VRAM tier or with overlapping
  target tasks, so the catalog won't generate nonsense pairs as it grows).
- `generateProviderPairs()` — every provider pair (no filter; any two
  providers are worth comparing).
- `canonicalPairSlug(idA, idB)` — always alphabetically orders the two ids,
  so `h100-vs-a100` and `a100-vs-h100` can never both exist as separate
  pages. Every place that links to a `/compare/` page (footer, GPU detail
  page, the compare page's own "related comparisons") goes through this.
- `resolveComparison(slug)` — parses `[a]-vs-[b]` back into a typed GPU or
  Provider pair for the page to render; `isValidPairSlug()` wraps it as a
  boolean check.

`src/lib/compareContent.ts` builds all the templated copy for a pair (side-
by-side table rows with a computed row "winner", the AI Verdict one-liner,
pros/cons, and 3 FAQ items) purely from the GPU/Provider records — no
hand-written copy per page.

## Live price sync (`scripts/fetch-prices.ts`)

`npm run sync-prices` polls provider pricing APIs and rewrites
`src/data/providers.json` + `src/data/gpus.json` in place, before every
`npm run build` (`"build": "npm run sync-prices && astro check && astro build"`).
It's designed to never break a build: every provider fetcher catches its own
errors and falls back to keeping the currently-committed price rather than
throwing.

| Provider | Source | Behavior without config |
|---|---|---|
| **Vast.ai** | Public `bundles` marketplace endpoint, no auth | Runs as-is; on any HTTP/network failure, keeps existing prices |
| **RunPod** | GraphQL `gpuTypes` query, requires an API key | No-ops (not an error) if `RUNPOD_API_KEY` isn't set |
| **Hyperstack** | Infrahub API — `/core/flavors` + `/pricebook`, requires an API key | No-ops (not an error) if `HYPERSTACK_API_KEY` isn't set |
| **Thunder Compute** | `/v2/pricing` + `/v2/specs`, requires an API key | No-ops (not an error) if `THUNDER_API_KEY` isn't set |
| **CloudRift** | `api.cloudrift.ai/api/v1/instance-types/list`, no auth — via `gpuhunt` (see below) | Runs as-is; on any failure (including Python/gpuhunt missing), keeps existing prices |
| **JarvisLabs** | `/misc/server_meta`, requires an API key — via `gpuhunt` (see below) | No-ops (not an error) if `JARVISLABS_API_KEY` isn't set |
| **Hot Aisle** | `admin.hotaisle.app/.../virtual_machines/available/`, requires an API key + team handle — via `gpuhunt` (see below) | No-ops (not an error) if `HOTAISLE_API_KEY`/`HOTAISLE_TEAM_HANDLE` aren't set. AMD MI300X/MI355X only, no NVIDIA. |
| **Paperspace, Novita AI** | No confirmed stable public pricing API | Always keeps the last committed price (documented fetcher stub — swap in a real integration per provider once one's confirmed) |

CloudRift, JarvisLabs and Hot Aisle are the one exception to "every fetcher
is a plain Node `fetch` call": all three are routed through
[`gpuhunt`](https://github.com/dstackai/gpuhunt) (MPL-2.0), a real
open-source Python library that itself calls those providers' first-party
APIs — see `scripts/gpuhunt/fetch_gpuhunt.py` for the thin CLI wrapper and
the big comment in `scripts/fetch-prices.ts` (section 3f) for why. This
means `npm run sync-prices` needs a `python3`/`python` on `PATH` with
`pip install -r scripts/gpuhunt/requirements.txt` run once for those rows
to self-correct; without it, all three fetchers fail closed (keep the last
committed price) exactly like a missing API key does for everyone else —
it never breaks the build. Self-hosted Docker bakes this venv into the
image already (see the Dockerfile); the static-host CI path
(`.github/workflows/daily-sync.yml`) sets it up with `actions/setup-python`
before `npm run sync-prices`. Set `GPUHUNT_PYTHON_BIN` to point at a
specific interpreter instead of relying on `PATH` lookup (this is how the
Docker image wires up its venv).

Not every provider `gpuhunt` supports gets added here, though — **Vultr**
is also auth-free but was deliberately left out after checking its actual
catalog: its GPU "offers" are either fractional vGPU slices (a 2-8GB
sliver of an A16/A40, not the full card — the instance names literally end
in `-2vram`/`-4vram`) or one 8-GPU-only bare-metal bundle with no
single-GPU price at all. Neither fits this schema's per-full-GPU hourly
rate without either mislabeling a fraction as a full card or fabricating a
per-GPU number by dividing a bundle price — so it stays out rather than
show something misleading.

`normalizeGpuName()` maps each provider's raw GPU string ("GeForce RTX 4090
24GB", "H100 SXM5", …) down to our catalog ids; anything that doesn't match
a known card is logged and skipped rather than silently dropped or
guessed. The script only ever updates a `(provider, GPU)` row that already
exists in `providers.json` — it won't auto-append an unfamiliar offer,
since it can't fill in fields like `rating` or `regions` an API doesn't
provide. `src/data/gpus.json` then gets a denormalized `market` snapshot
per GPU (min on-demand/spot price, summed live availability where a
provider reports a count, and a `last_updated` timestamp) — see
`GpuMarketSnapshot` in `src/types/index.ts`.

Two ways to keep this running on a schedule — self-hosted Docker
(re-syncs itself, no CI) or a static host + `.github/workflows/daily-sync.yml`
(commits fresh prices to `main`, host redeploys on push). Full setup steps
for both, plus every environment variable involved, are in
**[DEPLOYMENT.md](DEPLOYMENT.md)** — this section is about how the sync
logic itself works, not how to run it.

## Self-hosting with Docker

One container, no external CI: `docker/entrypoint.sh` re-runs
`npm run sync-prices` + rebuilds the Astro site **inside the running
container** on an interval, and nginx serves the result. Nothing pushes to
GitHub and nothing needs to redeploy the image for prices to stay fresh.
See [DEPLOYMENT.md](DEPLOYMENT.md) for the actual `docker compose`
commands and domain/TLS setup — this section covers how the refresh loop
and image are built.

**How the refresh loop works** (`docker/entrypoint.sh`):

1. On container start, and then every `SYNC_INTERVAL_HOURS` (default `6`,
   set in `docker-compose.yaml`): runs `npm run sync-prices`, then
   `astro build` into `dist.new/`.
2. On success, atomically swaps `dist.new/` in for `dist/` (`mv` on the
   same filesystem) — nginx, which serves straight from `/app/dist`, never
   sees a half-written directory and needs no restart to pick up the
   change.
3. On failure (a provider API down, a bad build), the currently-served
   `dist/` is left completely untouched — a bad sync never takes the site
   offline.

Image layout: `node:20-alpine` + `nginx`, `docker build` bakes one initial
`dist/` (this is the only point `astro check` runs — a broken build fails
`docker build`, not a live container), then `docker/entrypoint.sh` takes
over both serving and the refresh loop at runtime. There's no multi-stage
slim final image, since the container needs the full Node toolchain
present at runtime to keep rebuilding, not just to serve static files.

## SEO

- Per-page `<title>`, meta description, canonical URL, OpenGraph + Twitter
  Card tags via `src/components/SeoHead.astro` (`src/lib/seo.ts`)
- JSON-LD: `Product` + `AggregateRating` on GPU pages, `FAQPage` on every FAQ
  block, `BreadcrumbList` on every page with breadcrumbs
  (`src/lib/schema.ts`, dropped in via `src/components/JsonLd.astro`)
- `sitemap.xml` + `robots.txt` generated automatically at build

## Performance choices

- Static output (`output: "static"` in `astro.config.mjs`) — every route is
  plain HTML at build time, no server round-trip
- Only the homepage filter table hydrates as a client island
  (`client:load` on `<GpuFilterTable />`); everything else (badges,
  breadcrumbs, FAQ accordions, CTA buttons) ships zero JavaScript
- `compressHTML: true` + `inlineStylesheets: "auto"` in Astro config

## Local development

```bash
cd gpu-cloud-compare
npm install
pip install -r scripts/gpuhunt/requirements.txt  # optional — only needed for the
                                                  # CloudRift/JarvisLabs live fetchers;
                                                  # everything else works without it
npm run dev          # http://localhost:4321
npm run sync-prices  # refresh src/data/*.json from live provider APIs
npm run build        # sync-prices + astro check + static build -> dist/
npm run preview      # serve the production build locally
```

## Extending

- **Add a GPU:** append to `src/data/gpus.json`, then add matching offers to
  `providers.json` — `/gpu/[slug]`, the homepage table and every
  `/compare/*` pair page regenerate automatically.
- **Add a provider:** append offer rows to `providers.json` with a new
  `slug`; provider-vs-provider comparison pages are generated for every pair
  automatically by `src/utils/pseo.ts`.
- **Add a use case:** append to `use-cases.json` with a `recommended_gpu_ids`
  list; `/best-gpu-for/[slug]` and its FAQ are generated automatically.
- **Wire up a real pricing API for a static-fallback provider:** add a
  `fetchXPrices()` function to `scripts/fetch-prices.ts` following the
  `fetchVastPrices`/`fetchRunPodPrices` pattern (fetch, normalize with
  `normalizeGpuName`, return `RawOffer[]`, catch-and-fallback on error) and
  add it to the `Promise.allSettled([...])` list in `main()`.
