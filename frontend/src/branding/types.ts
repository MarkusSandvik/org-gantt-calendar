export type ThemePreference = "light" | "dark" | "system";

export interface BrandingConfig {
  id: string;
  productName: string;
  /** Short secondary line shown under the product name on Login, e.g.
   * "Project Control". Omit for orgs that don't need one. */
  tagline?: string;
  faviconHref: string;
  /** Wordmark/logo shown in the nav and on Login. Falls back to a text-only
   * productName when absent — no org is required to supply a logo image. */
  logoHref?: string;
  /** Icon-only mark (no wordmark text), used where space is tight or
   * circular — e.g. the annual wheel's center hub. Falls back to a plain
   * hub with no image when absent. */
  iconHref?: string;
  /** Applied before a visitor has made an explicit theme choice (see
   * useTheme.ts). Falls back to "system" when absent. */
  defaultTheme?: ThemePreference;
  /** Optional public-facing site, shown subtly on Login when present. */
  websiteUrl?: string;
  /** Appended to the nav footer's "Created by <author>" credit, e.g.
   * "for Vortex NTNU". Omit for orgs that don't need one. */
  creditSuffix?: string;
  features: Record<string, boolean>;
}
