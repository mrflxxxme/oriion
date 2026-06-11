/**
 * PasswordStrengthMeter — a 3-segment bar scoring length + character classes.
 * Pure (no deps). Exposes an aria-live=polite status so screen readers hear
 * strength changes; pair its `id` with the password input's aria-describedby.
 */
import { t } from "@/lib/i18n";

export interface PasswordStrengthMeterProps {
  /** The current password value. */
  value: string;
  /** Element id so the password input can reference it via aria-describedby. */
  id: string;
}

type Strength = 0 | 1 | 2 | 3;

/** Score a password into weak (1) / medium (2) / strong (3); 0 when empty. */
function scorePassword(value: string): Strength {
  if (value.length === 0) return 0;

  let classes = 0;
  if (/[a-z]/.test(value)) classes += 1;
  if (/[A-Z]/.test(value)) classes += 1;
  if (/\d/.test(value)) classes += 1;
  if (/[^A-Za-z0-9]/.test(value)) classes += 1;

  if (value.length >= 12 && classes >= 3) return 3;
  if (value.length >= 8 && classes >= 2) return 2;
  return 1;
}

const LABELS: Record<Exclude<Strength, 0>, string> = {
  1: t("auth.strength.weak"),
  2: t("auth.strength.medium"),
  3: t("auth.strength.strong"),
};

const SEGMENT_COLOR: Record<Exclude<Strength, 0>, string> = {
  1: "bg-danger-600",
  2: "bg-warning-500",
  3: "bg-success-600",
};

export function PasswordStrengthMeter({ value, id }: PasswordStrengthMeterProps) {
  const strength = scorePassword(value);

  return (
    <div className="mt-2">
      <div className="flex gap-1" aria-hidden="true">
        {[1, 2, 3].map((segment) => (
          <div
            key={segment}
            className={
              strength >= segment && strength !== 0
                ? `h-1 flex-1 rounded-full ${SEGMENT_COLOR[strength]}`
                : "h-1 flex-1 rounded-full bg-default"
            }
          />
        ))}
      </div>
      <p id={id} aria-live="polite" className="mt-1 text-xs text-secondary">
        {strength === 0 ? "" : `${t("auth.strength.label")}: ${LABELS[strength]}`}
      </p>
    </div>
  );
}
