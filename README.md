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

## Motion candidate studies

The first production sprint draft has 18 whole-raster motion studies under `public/motion-candidates-v1/`. Each candidate contains twelve 768px WebP frames and a looping WebP preview at 24 fps. They are retained as a visual comparison set; they do not define the element-level motion contract. Run `npm run motion:generate` to recreate them from the source artwork; the generator requires Pillow, NumPy, and OpenCV in the active Python environment.

After `npm run build` and `npm run preview`, open `/motion-candidates-v1/` to compare the loops and expand any card to inspect its twelve frames. These are shortlist studies; the selected nine should be encoded into final WebM and MP4 delivery assets after review.

## Element-level motion pilots

The corrected pilot is under `public/motion-pilots-v2/`. It uses the same 12-frame, 24 fps contract, but composes each frame from an unchanged source artwork and a transparent overlay for the named moving elements. The generator records the locked-region check in `public/motion-pilots-v2/metadata.json`:

    npm run motion:pilots

After a build and preview, open `/motion-pilots-v2/` to compare the static source, composite loop, and transparent motion layer for IDs 066 and 080. The v1 whole-raster studies remain available for comparison while the layer boundary is being reviewed.

## Acknowledgment

This is a personal devotional and creative project. I am grateful to the artists, illustrators, animators, storytellers, and creators whose work and imagination inspired these explorations, and to OpenAI for the creative tools that helped me explore them.

Some works are inspired by recognizable characters and storyworlds. They are personal, unofficial AI-assisted interpretations and are not sponsored by, affiliated with, or endorsed by the original creators or rights holders. The collection does not claim participation or endorsement from the people or organizations acknowledged.

## Publication

The static build is designed for GitHub Pages. The workflow under .github/workflows/pages.yml is manual so a push to the source repository does not publish the site by itself.
