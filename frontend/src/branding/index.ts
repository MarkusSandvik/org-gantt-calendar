import type { BrandingConfig } from "./types";
import { branding as defaultBranding } from "./profiles/default";
import { branding as vortexBranding } from "./profiles/vortex";

const PROFILES: Record<string, BrandingConfig> = {
  default: defaultBranding,
  vortex: vortexBranding,
};

function resolveBranding(): BrandingConfig {
  const orgId = import.meta.env.VITE_ORGANIZATION || "default";
  const profile = PROFILES[orgId];
  if (!profile) {
    throw new Error(
      `Unknown VITE_ORGANIZATION="${orgId}" — no branding profile registered in ` +
        `frontend/src/branding/index.ts. Set VITE_ORGANIZATION to an existing profile id, ` +
        `or add a new one (see ORGANIZATION_PLAN.md).`,
    );
  }
  return profile;
}

export const branding = resolveBranding();
export type { BrandingConfig };
