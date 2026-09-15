import assert from "node:assert/strict";
import { access, readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const galleriesData = JSON.parse(await readFile(path.join(root, "src/data/galleries.json"), "utf8"));
const artworks = JSON.parse(await readFile(path.join(root, "src/data/artworks.json"), "utf8"));
const selectedIds = galleriesData.galleries.flatMap((gallery) => gallery.members);
const sourceFiles = await readdir(path.join(root, "src/assets/artworks"));

assert.equal(galleriesData.galleries.length, 9, "Expected nine galleries");
assert.equal(selectedIds.length, 108, "Expected 108 gallery placements");
assert.equal(new Set(selectedIds).size, 108, "Every artwork must appear once");
assert.equal(artworks.length, 108, "Expected 108 artwork records");
assert.equal(new Set(artworks.map((artwork) => artwork.sourceSha256)).size, 108, "Source artworks must be unique");
assert.equal(sourceFiles.length, 108, "Expected exactly 108 optimized source images");

for (const gallery of galleriesData.galleries) {
  assert.equal(gallery.members.length, 12, `${gallery.title} must contain twelve works`);
  const pagePath = path.join(root, "dist/galleries", gallery.slug, "index.html");
  const html = await readFile(pagePath, "utf8");
  const renderedIds = [...html.matchAll(/data-artwork-id="(\d{3})"/g)].map((match) => match[1]);
  assert.deepEqual(renderedIds, gallery.members, `${gallery.title} page must render its twelve works in order`);
}

const configuredBase = process.env.SITE_BASE || "/";
const base = configuredBase === "/" ? "" : `/${configuredBase.replace(/^\/+|\/+$/g, "")}`;
const internalPrefix = base ? `${base}/` : "/";

function localPathname(value) {
  return value.trim().split(/[?#]/, 1)[0];
}

function isRootAbsolutePath(value) {
  const pathname = localPathname(value);
  // Protocol-relative URLs (//example.com/...) are external URLs, even
  // though they begin with a slash. Relative URLs and fragments do not need
  // a base-prefix check here.
  return pathname.startsWith("/") && !pathname.startsWith("//");
}

function hasConfiguredBase(value) {
  const pathname = localPathname(value);
  return base === "" || pathname === base || pathname.startsWith(internalPrefix);
}

function assertInternalUrl(file, attribute, value) {
  if (isRootAbsolutePath(value)) {
    assert.ok(
      hasConfiguredBase(value),
      `${file} contains a broken base-path URL in ${attribute}: ${value}`,
    );
  }
}

function verifyUrlAttributes(file, html) {
  const attributePattern = /\b(href|src|srcset|data-artwork-src|style)\s*=\s*(["'])([\s\S]*?)\2/gi;

  for (const [, attribute, value] of html.matchAll(attributePattern)) {
    if (attribute.toLowerCase() === "srcset") {
      // A srcset is a comma-separated list of candidates. The first token of
      // each candidate is its URL; the remaining tokens are width or density
      // descriptors. This also leaves data/blob/external URLs untouched.
      for (const candidate of value.split(",")) {
        const url = candidate.trim().split(/\s+/, 1)[0];
        if (url) assertInternalUrl(file, attribute, url);
      }
      continue;
    }

    if (attribute.toLowerCase() === "style") {
      const styleUrlPattern = /url\(\s*(?:(["'])([\s\S]*?)\1|([^)]*?))\s*\)/gi;
      for (const [, , quotedUrl, unquotedUrl] of value.matchAll(styleUrlPattern)) {
        const url = (quotedUrl ?? unquotedUrl).trim();
        if (url) assertInternalUrl(file, attribute, url);
      }
      continue;
    }

    assertInternalUrl(file, attribute, value);
  }
}

const routes = [
  { file: "index.html", route: "/" },
  ...galleriesData.galleries.map((gallery) => ({
    file: path.join("galleries", gallery.slug, "index.html"),
    route: `/galleries/${gallery.slug}/`,
  })),
];

for (const { file, route } of routes) {
  const html = await readFile(path.join(root, "dist", file), "utf8");
  const canonical = html.match(/<link rel="canonical" href="([^"]+)"/);
  assert.ok(canonical, `${file} must have a canonical URL`);
  assert.equal(new URL(canonical[1]).pathname, `${base}${route}`, `${file} canonical path must match its route`);
  verifyUrlAttributes(file, html);
  for (const [, asset] of html.matchAll(/\/_astro\/([^/?#"'()\s]+)/g)) {
    await access(path.join(root, "dist/_astro", asset));
  }
}

console.log(`Verified ${galleriesData.galleries.length} galleries, ${artworks.length} unique works, and ${routes.length} static routes.`);
