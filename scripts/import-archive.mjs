import fs from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import process from "node:process";
import sharp from "sharp";

const projectRoot = path.resolve(import.meta.dirname, "..");
const archiveRoot = process.argv[2] ? path.resolve(process.argv[2]) : "";
const checkOnly = process.argv[3] === "--check-only";

if (!archiveRoot) {
  console.error("Usage: npm run import:archive -- <archive-root>");
  process.exit(1);
}

function parseCsvLine(line) {
  const fields = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"' && quoted && line[index + 1] === '"') {
      field += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      fields.push(field);
      field = "";
    } else {
      field += character;
    }
  }
  fields.push(field);
  return fields;
}

function parseCsv(input) {
  const lines = input.replace(/^\uFEFF/, "").trimEnd().split(/\r?\n/);
  const headers = parseCsvLine(lines.shift());
  return lines.map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

function slugFromFilename(filename) {
  return filename
    .replace(/\.(png|webp)$/i, "")
    .replace(/^\d+-/, "");
}

const galleryData = JSON.parse(
  await fs.readFile(path.join(projectRoot, "src/data/galleries.json"), "utf8"),
);
const allIds = galleryData.galleries.flatMap((gallery) => gallery.members);
const uniqueIds = new Set(allIds);

if (galleryData.galleries.length !== 9 || allIds.length !== 108 || uniqueIds.size !== 108) {
  throw new Error("Gallery taxonomy must contain exactly nine groups and 108 unique IDs.");
}
if (allIds.includes("093") || allIds.includes("094")) {
  throw new Error("The duplicate #093 and excluded LEGO #094 must remain outside the public set.");
}
if (galleryData.galleries.some((gallery) => gallery.members.length !== 12)) {
  throw new Error("Every gallery must contain exactly twelve artworks.");
}

const indexPath = path.join(archiveRoot, "ganesha-review", "MASTER_INDEX.csv");
const rows = parseCsv(await fs.readFile(indexPath, "utf8"));
const rowById = new Map(rows.map((row) => [row.archive_number, row]));
const sourcePaths = new Set();
const outputFilenames = new Set();
const output = [];
const outputDirectory = path.join(projectRoot, "src/assets/artworks");
const imports = [];

for (const gallery of galleryData.galleries) {
  for (const id of gallery.members) {
    const row = rowById.get(id);
    if (!row || !row.main_image_path || !row.concept) {
      throw new Error("Missing manifest row or image information for archive ID " + id + ".");
    }
    if (row.selection_status === "REMOVE" || row.keep_for_final_108 === "NO") {
      throw new Error("Archive ID " + id + " is explicitly excluded from the selected collection.");
    }

    const sourcePath = path.resolve(archiveRoot, row.main_image_path);
    const sourceStat = await fs.stat(sourcePath).catch(() => null);
    if (!sourceStat || !sourceStat.isFile()) {
      throw new Error("Image source does not exist for #" + id + ": " + row.main_image_path);
    }
    if (!/^[a-f\d]{64}$/i.test(row.sha256 ?? "")) {
      throw new Error("Missing or invalid SHA-256 checksum in the archive index for #" + id + ".");
    }
    if (sourcePaths.has(sourcePath)) {
      throw new Error("An image source is assigned more than once: " + row.main_image_path);
    }
    sourcePaths.add(sourcePath);

    const sourceHash = createHash("sha256").update(await fs.readFile(sourcePath)).digest("hex");
    if (sourceHash !== row.sha256.toLowerCase()) {
      throw new Error("SHA-256 mismatch for archive ID " + id + ": " + row.main_image_path);
    }

    const sourceFilename = path.basename(row.main_image_path);
    const filename = sourceFilename.replace(/\.png$/i, ".webp");
    if (outputFilenames.has(filename)) {
      throw new Error("Two selected source images would write the same output filename: " + filename);
    }
    outputFilenames.add(filename);
    imports.push({ sourcePath, filename });

    output.push({
      id,
      title: row.concept,
      alt: "AI-assisted artwork exploring " + row.concept + ".",
      file: filename,
      slug: slugFromFilename(filename),
      groupSlug: gallery.slug,
      groupTitle: gallery.title,
      sourceSha256: sourceHash,
    });
  }
}

if (new Set(output.map((item) => item.sourceSha256)).size !== 108) {
  throw new Error("The selected source set does not contain 108 unique image contents.");
}

if (checkOnly) {
  console.log("Verified " + output.length + " source files and SHA-256 hashes across " + galleryData.galleries.length + " groups. No files were changed.");
} else {
  await fs.mkdir(outputDirectory, { recursive: true });

  // Only numbered WebP files are owned by this importer. Preserve any other
  // files that a contributor may keep in the artwork directory.
  for (const entry of await fs.readdir(outputDirectory, { withFileTypes: true })) {
    if (!entry.isFile() || !/^\d{3}-.+\.webp$/i.test(entry.name) || outputFilenames.has(entry.name)) {
      continue;
    }
    await fs.unlink(path.join(outputDirectory, entry.name));
  }

  for (const { sourcePath, filename } of imports) {
    await sharp(sourcePath)
      .rotate()
      .resize({ width: 1600, height: 1600, fit: "inside", withoutEnlargement: true })
      .webp({ quality: 88, effort: 6 })
      .toFile(path.join(outputDirectory, filename));
  }

  await fs.writeFile(
    path.join(projectRoot, "src/data/artworks.json"),
    JSON.stringify(output, null, 2) + "\n",
  );
  console.log("Imported " + output.length + " unique artworks across " + galleryData.galleries.length + " groups.");
  console.log("Generated web-ready WebP sources in " + path.relative(projectRoot, outputDirectory) + ".");
}
