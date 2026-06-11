/**
 * ConsentBlock — ФЗ-152 consent (required) + optional marketing opt-in.
 *
 * Radix Checkbox is controlled, so each box is bridged to react-hook-form via
 * <Controller>. The required-consent error is announced with role=alert and
 * linked to the box through aria-describedby.
 */
import { Controller, type Control } from "react-hook-form";
import { Checkbox } from "@/components/ui";
import { t } from "@/lib/i18n";
import type { RegisterValues } from "../schemas";

export interface ConsentBlockProps {
  control: Control<RegisterValues>;
  /** Validation message for the required PDN consent, if any. */
  consentError: string | undefined;
}

export function ConsentBlock({ control, consentError }: ConsentBlockProps) {
  const errorId = "consent-pdn-error";

  return (
    <fieldset className="flex flex-col gap-3 border-0 p-0">
      <Controller
        control={control}
        name="consentPdn"
        render={({ field }) => (
          <div className="flex flex-col gap-1">
            <div className="flex items-start gap-2">
              <Checkbox
                id="consentPdn"
                checked={field.value}
                onCheckedChange={(checked) => {
                  field.onChange(checked === true);
                }}
                onBlur={field.onBlur}
                aria-invalid={consentError ? true : undefined}
                aria-describedby={consentError ? errorId : undefined}
                className="mt-0.5"
              />
              <label
                htmlFor="consentPdn"
                className="text-sm text-primary cursor-pointer select-none"
              >
                {t("auth.consent.pdn")}
              </label>
            </div>
            {consentError ? (
              <p id={errorId} role="alert" className="text-xs text-danger-600">
                {consentError}
              </p>
            ) : null}
          </div>
        )}
      />

      <Controller
        control={control}
        name="consentMarketing"
        render={({ field }) => (
          <div className="flex items-start gap-2">
            <Checkbox
              id="consentMarketing"
              checked={field.value ?? false}
              onCheckedChange={(checked) => {
                field.onChange(checked === true);
              }}
              onBlur={field.onBlur}
              className="mt-0.5"
            />
            <label
              htmlFor="consentMarketing"
              className="text-sm text-primary cursor-pointer select-none"
            >
              {t("auth.consent.marketing")}
            </label>
          </div>
        )}
      />
    </fieldset>
  );
}
