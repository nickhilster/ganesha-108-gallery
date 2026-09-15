import type { ImageMetadata } from "astro";

const modules = import.meta.glob<{ default: ImageMetadata }>("../assets/artworks/*.webp", {
  eager: true,
});
const images = Object.fromEntries(
  Object.entries(modules).map(([path, module]) => [path.split("/").at(-1), module.default]),
);

export function getArtworkImage(filename: string): ImageMetadata {
  const image = images[filename] as ImageMetadata | undefined;
  if (!image) {
    throw new Error("Missing artwork asset: " + filename);
  }
  return image;
}
