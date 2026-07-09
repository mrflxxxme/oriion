/**
 * Onboarding preset catalog (Phase 01.12) — the 3 Wave-1 presets the wizard
 * offers, each with a prefilled demo first-task ("3 demo scenarios").
 *
 * `key` is the `team_preset.slug` sent to POST /cells/{cell_id}/teams
 * (`preset_key`) — it must match a seeded preset:
 *   - "productivity-core"     (horizontal base)
 *   - "agency-marketing-ru"   (vertical, Master + marketing team)
 *   - "telegram-creator"      (vertical, Master + community-manager)
 * All three now route through team_provisioning_service (the telegram-creator
 * routing gap was closed in this phase's backend change).
 *
 * `demoTitle` is a short human title; `demoPrompt` is the prefilled first-task
 * prompt for that preset. Both are i18n keys resolved by the wizard.
 */
import type { I18nKey } from "@/lib/i18n";

export type PresetKey = "productivity-core" | "agency-marketing-ru" | "telegram-creator";

export interface OnboardingPreset {
  key: PresetKey;
  titleKey: I18nKey;
  descriptionKey: I18nKey;
  demoTitleKey: I18nKey;
  demoPromptKey: I18nKey;
}

export const ONBOARDING_PRESETS: OnboardingPreset[] = [
  {
    key: "productivity-core",
    titleKey: "onboarding.preset.productivityCore.title",
    descriptionKey: "onboarding.preset.productivityCore.description",
    demoTitleKey: "onboarding.preset.productivityCore.demoTitle",
    demoPromptKey: "onboarding.preset.productivityCore.demoPrompt",
  },
  {
    key: "agency-marketing-ru",
    titleKey: "onboarding.preset.agencyMarketingRu.title",
    descriptionKey: "onboarding.preset.agencyMarketingRu.description",
    demoTitleKey: "onboarding.preset.agencyMarketingRu.demoTitle",
    demoPromptKey: "onboarding.preset.agencyMarketingRu.demoPrompt",
  },
  {
    key: "telegram-creator",
    titleKey: "onboarding.preset.telegramCreator.title",
    descriptionKey: "onboarding.preset.telegramCreator.description",
    demoTitleKey: "onboarding.preset.telegramCreator.demoTitle",
    demoPromptKey: "onboarding.preset.telegramCreator.demoPrompt",
  },
];

export function findPreset(key: PresetKey): OnboardingPreset {
  const preset = ONBOARDING_PRESETS.find((p) => p.key === key);
  // Every PresetKey has a catalog entry — this is exhaustive by construction.
  if (!preset) throw new Error(`unknown onboarding preset: ${key}`);
  return preset;
}
