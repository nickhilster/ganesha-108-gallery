import { defineConfig } from "astro/config";

const siteBase = process.env.SITE_BASE || "/";

export default defineConfig({
  site: process.env.SITE_URL || "https://ganesha-108-gallery.vercel.app",
  base: siteBase,
  output: "static",
  build: {
    format: "directory",
  },
  image: {
    responsiveStyles: true,
  },
});
