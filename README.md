# Ganesha 108

A mobile-first gallery for 108 unique, AI-assisted Ganesha artworks. The images are arranged into nine conceptual collections of twelve; the collection order is thematic, not chronological.

## Run locally

Run npm install, then npm run dev.

To build and preview the static site, run npm run build and npm run preview.

Local builds use the site root by default. The Pages workflow sets `SITE_BASE=/ganesha-108-gallery`; to preview that deployment layout locally, set the same environment variable for both the build and verification commands.

## Archive and image preparation

The source archive stays separate from this publication repository. To refresh the selected web-ready images and manifest from the archive, run:

    npm run import:archive -- "C:\dev\Ganesha 108"

To validate the selected archive files and their SHA-256 hashes without rewriting the web assets, run:

    npm run import:archive -- "C:\dev\Ganesha 108" --check-only

The import script takes only the selected IDs in src/data/galleries.json, validates the 108-image count and unique hashes, and writes optimized WebP sources to src/assets/artworks/. It does not move or alter archive files. Astro creates responsive delivery variants at build time.

## Acknowledgment

This is a personal devotional and creative project. I am grateful to the artists, illustrators, animators, storytellers, and creators whose work and imagination inspired these explorations, and to OpenAI for the creative tools that helped me explore them.

Some works are inspired by recognizable characters and storyworlds. They are personal, unofficial AI-assisted interpretations and are not sponsored by, affiliated with, or endorsed by the original creators or rights holders. The collection does not claim participation or endorsement from the people or organizations acknowledged.

## Publication

The static build is designed for GitHub Pages. The workflow under .github/workflows/pages.yml is manual so a push to the source repository does not publish the site by itself.
