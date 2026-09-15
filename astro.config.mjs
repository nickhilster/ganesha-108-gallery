import { defineConfig } from "astro/config";

const siteBase = process.env.SITE_BASE || "/";

export default defineConfig({
  site: "https://nickhilster.github.io",
  base: siteBase,
  output: "static",
  build: {
    format: "directory",
  },
  image: {
    responsiveStyles: true,
  },
});
