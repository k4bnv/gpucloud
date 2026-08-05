#!/usr/bin/env python3
"""
scripts/gpuhunt/fetch_gpuhunt.py

Thin CLI wrapper around `gpuhunt` (github.com/dstackai/gpuhunt, MPL-2.0) —
a genuinely open-source Python library that calls each cloud provider's own
first-party API, unlike price-comparison sites such as gpus.io or
gputracker.dev whose Terms of Service explicitly forbid feeding their data
into a competing comparison product (see README.md's "Live price sync"
section). We only use gpuhunt for providers where it has a real, working,
*live* API integration we haven't hand-written a TypeScript fetcher for —
today that's CloudRift (no API key) and JarvisLabs (needs JL_API_KEY).

This script is deliberately dumb: fetch raw catalog items for ONE provider,
print them as a JSON array to stdout, and never raise. All GPU-name
normalization and merging into providers.json/gpus.json happens back in
scripts/fetch-prices.ts, same as every other fetcher there — this is just
the transport across the Node/Python boundary.

Usage:
    python fetch_gpuhunt.py <provider-name>

Exit code is always 0. On any failure — gpuhunt not installed, missing
credentials, upstream API error — prints `[]` and a diagnostic line to
stderr instead of raising, matching the "never break a build" contract
scripts/fetch-prices.ts relies on for every other provider.
"""

import json
import os
import re
import sys


def normalize_spacing(gpu_name: str) -> str:
    """
    gpuhunt's raw `gpu_name` is sometimes vendor-prefix + digits with no
    separator ("RTX4090", "RTX5090"), whereas
    scripts/fetch-prices.ts's normalizeGpuName() matches on word-boundary
    tokens like "rtx 4090" — `\\b4090\\b` never matches inside "rtx4090"
    because digits and letters are both `\\w`, so there's no boundary
    between "t" and "4". Insert the space back for known multi-word
    prefixes only ("H100", "A100", "T4", "L40S", ... already match fine as
    single un-spaced tokens and must be left alone).
    """
    return re.sub(r"^(RTX|GTX)(\d)", r"\1 \2", gpu_name, flags=re.IGNORECASE)


def build_provider(name: str):
    """Construct a gpuhunt AbstractProvider instance for `name`, or raise."""
    if name == "cloudrift":
        # Public, unauthenticated endpoint — see the CloudRiftProvider
        # source for the exact `api.cloudrift.ai` call.
        from gpuhunt.providers.cloudrift import CloudRiftProvider

        return CloudRiftProvider()

    if name == "jarvislabs":
        # gpuhunt's own JarvisLabsProvider only reads its internal
        # JL_API_KEY env var name; our .env convention (matching every
        # other provider in this project) is JARVISLABS_API_KEY, so bridge
        # the two here instead of asking users to know gpuhunt's name too.
        from gpuhunt.providers.jarvislabs import JarvisLabsProvider

        api_key = os.getenv("JARVISLABS_API_KEY")
        if not api_key:
            raise RuntimeError("JARVISLABS_API_KEY not set")
        return JarvisLabsProvider(api_key=api_key)

    if name == "hotaisle":
        # Unlike JarvisLabs, gpuhunt's HotAisleProvider already reads
        # HOTAISLE_API_KEY/HOTAISLE_TEAM_HANDLE directly (no name mismatch
        # to bridge) — AMD-only shop (MI300X/MI355X), no NVIDIA offers.
        from gpuhunt.providers.hotaisle import HotAisleProvider

        if not os.getenv("HOTAISLE_API_KEY"):
            raise RuntimeError("HOTAISLE_API_KEY not set")
        if not os.getenv("HOTAISLE_TEAM_HANDLE"):
            raise RuntimeError("HOTAISLE_TEAM_HANDLE not set")
        return HotAisleProvider()

    if name == "verda":
        # Unlike JarvisLabs/HotAisle, VerdaProvider doesn't read env vars
        # itself — its constructor takes client_id/client_secret directly
        # (passed straight to the `verda` SDK's VerdaClient) — so we read
        # our own env var names and pass them through explicitly.
        from gpuhunt.providers.verda import VerdaProvider

        client_id = os.getenv("VERDA_CLIENT_ID")
        client_secret = os.getenv("VERDA_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("VERDA_CLIENT_ID / VERDA_CLIENT_SECRET not set")
        return VerdaProvider(client_id, client_secret)

    raise RuntimeError(f"unknown gpuhunt provider {name!r}")


def main() -> None:
    if len(sys.argv) != 2:
        print("[]")
        print("usage: fetch_gpuhunt.py <provider-name>", file=sys.stderr)
        return

    provider_name = sys.argv[1]

    try:
        provider = build_provider(provider_name)
        items = provider.get()
    except Exception as exc:  # noqa: BLE001 - intentionally catch-all, see module docstring
        print("[]")
        print(f"[gpuhunt:{provider_name}] {exc}", file=sys.stderr)
        return

    out = [
        {
            "gpu_name": normalize_spacing(item.gpu_name),
            "gpu_count": item.gpu_count,
            "price": item.price,
            "spot": bool(item.spot),
        }
        for item in items
    ]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
