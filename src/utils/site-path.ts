export function sitePath(path = ""): string {
  const configuredBase = import.meta.env.BASE_URL;
  const base = configuredBase.endsWith("/") ? configuredBase : configuredBase + "/";
  const suffix = path.replace(/^\/+/, "");
  return base + suffix;
}
