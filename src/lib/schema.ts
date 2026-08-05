import type { ComputedOffer, FaqItem, GPU } from "@/types";
import { canonicalUrl, SITE_NAME, SITE_URL } from "@/lib/seo";

/**
 * Schema.org JSON-LD builders. Each function returns a plain object ready
 * to be dropped into `<script type="application/ld+json">` via
 * `JSON.stringify` — see `src/components/JsonLd.astro`.
 */

/**
 * Real off-site profile URLs for the `sameAs` entity graph (Organization
 * schema below). This is what tells Google/AI crawlers "this LinkedIn page,
 * this GitHub org, etc. are all the same entity as this website" — never
 * fabricate one of these, an unowned or dead URL here is worse than
 * omitting it. Comma-separated list, e.g.:
 *   SOCIAL_URLS=https://www.linkedin.com/company/...,https://github.com/...
 * Unset = `sameAs` is simply omitted from the schema.
 */
function getSameAsUrls(): string[] {
  return (process.env.SOCIAL_URLS ?? "")
    .split(",")
    .map((url) => url.trim())
    .filter(Boolean);
}

/**
 * Sitewide Organization schema — dropped on every page via BaseLayout. This
 * is the entity graph anchor: it's what lets Google (and AI Overview /
 * other LLM-backed search) resolve "gpucompare.cloud" and "the GPUCompare
 * LinkedIn page" etc. as the same real-world thing, rather than treating
 * every off-site mention as an unrelated, uncorroborated page.
 */
export function organizationSchema() {
  const sameAs = getSameAsUrls();
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
    logo: canonicalUrl("/favicon.svg"),
    ...(sameAs.length > 0 ? { sameAs } : {}),
  };
}

/** Sitewide WebSite schema — separate @type from Organization per schema.org convention (a site is not itself the org, it's published by the org). */
export function websiteSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: SITE_URL,
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
    },
  };
}

export interface BreadcrumbCrumb {
  name: string;
  path: string;
}

export function breadcrumbSchema(crumbs: BreadcrumbCrumb[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((crumb, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: crumb.name,
      item: canonicalUrl(crumb.path),
    })),
  };
}

export function faqSchema(faqs: FaqItem[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };
}

/**
 * Product + AggregateOffer + AggregateRating schema for a GPU detail page.
 * `offers` is a plain `AggregateOffer` (lowPrice/highPrice/offerCount) —
 * schema.org doesn't define a per-seller `offers` list nested inside
 * AggregateOffer, so we keep this strictly to the documented properties.
 * Rating is a review-count-weighted average across all providers renting it.
 */
export function gpuProductSchema(gpu: GPU, offers: ComputedOffer[]) {
  if (offers.length === 0) return null;

  const totalReviews = offers.reduce((sum, o) => sum + o.review_count, 0);
  const weightedRating =
    offers.reduce((sum, o) => sum + o.rating * o.review_count, 0) / totalReviews;

  const prices = offers.map((o) => o.price_on_demand);

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${gpu.name} Cloud Rental`,
    description: gpu.description,
    brand: {
      "@type": "Brand",
      name: gpu.vendor,
    },
    aggregateRating: {
      "@type": "AggregateRating",
      ratingValue: Number(weightedRating.toFixed(2)),
      reviewCount: totalReviews,
      bestRating: 5,
      worstRating: 1,
    },
    offers: {
      "@type": "AggregateOffer",
      priceCurrency: "USD",
      lowPrice: Math.min(...prices),
      highPrice: Math.max(...prices),
      offerCount: offers.length,
    },
  };
}
