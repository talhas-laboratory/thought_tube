export const META_SURFACE_PATH_PATTERN = /^\/meta(?:\/|$)/;
export const SELF_IMPROVEMENT_PATH_PATTERN = /^\/self-improvement(?:\/|$)/;

export function isServerOwnedSurfacePath(pathname: string): boolean {
  return (
    META_SURFACE_PATH_PATTERN.test(pathname) ||
    SELF_IMPROVEMENT_PATH_PATTERN.test(pathname)
  );
}
