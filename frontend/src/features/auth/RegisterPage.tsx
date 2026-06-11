/**
 * RegisterPage — sign-up wired to the live iam API with auto-login on success.
 * Renders inside AuthShell's centered column (no extra <h1>).
 */
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button, Card, Input } from "@/components/ui";
import { t } from "@/lib/i18n";
import type { RegisterPayload } from "@/api/auth";
import { registerSchema, type RegisterValues } from "./schemas";
import { useRegister } from "./hooks";
import { PasswordStrengthMeter } from "./components/PasswordStrengthMeter";
import { ConsentBlock } from "./components/ConsentBlock";

export function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegister();
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      passwordConfirm: "",
      displayName: "",
      consentPdn: false,
      consentMarketing: false,
    },
  });

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = form;

  const password = watch("password");

  const onValid = async (values: RegisterValues): Promise<void> => {
    const payload: RegisterPayload = {
      email: values.email,
      password: values.password,
      consent_pdn: values.consentPdn,
      ...(values.displayName ? { display_name: values.displayName } : {}),
      ...(values.consentMarketing !== undefined
        ? { consent_marketing: values.consentMarketing }
        : {}),
    };
    await registerMutation.mutateAsync(payload);
    await navigate({ to: "/cells" });
  };

  return (
    <Card variant="outlined" padding="lg">
      <Card.Header className="mb-6">
        <h2 className="text-xl font-semibold text-primary">{t("auth.register.title")}</h2>
      </Card.Header>
      <Card.Body>
        <form
          noValidate
          onSubmit={(e) => void handleSubmit(onValid)(e)}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-email" className="text-sm font-medium text-primary">
              {t("auth.field.email")}
            </label>
            <Input
              id="register-email"
              type="email"
              autoComplete="email"
              invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? "register-email-error" : undefined}
              {...register("email")}
            />
            {errors.email ? (
              <p id="register-email-error" role="alert" className="text-xs text-danger-600">
                {errors.email.message}
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-password" className="text-sm font-medium text-primary">
              {t("auth.field.password")}
            </label>
            <Input
              id="register-password"
              type="password"
              autoComplete="new-password"
              invalid={Boolean(errors.password)}
              aria-describedby={
                errors.password ? "register-password-error" : "register-password-strength"
              }
              {...register("password")}
            />
            <PasswordStrengthMeter id="register-password-strength" value={password} />
            {errors.password ? (
              <p id="register-password-error" role="alert" className="text-xs text-danger-600">
                {errors.password.message}
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-password-confirm" className="text-sm font-medium text-primary">
              {t("auth.field.passwordConfirm")}
            </label>
            <Input
              id="register-password-confirm"
              type="password"
              autoComplete="new-password"
              invalid={Boolean(errors.passwordConfirm)}
              aria-describedby={
                errors.passwordConfirm ? "register-password-confirm-error" : undefined
              }
              {...register("passwordConfirm")}
            />
            {errors.passwordConfirm ? (
              <p
                id="register-password-confirm-error"
                role="alert"
                className="text-xs text-danger-600"
              >
                {errors.passwordConfirm.message}
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="register-display-name" className="text-sm font-medium text-primary">
              {t("auth.field.displayName")}{" "}
              <span className="text-secondary font-normal">{t("common.optional")}</span>
            </label>
            <Input
              id="register-display-name"
              type="text"
              autoComplete="name"
              {...register("displayName")}
            />
          </div>

          <ConsentBlock control={control} consentError={errors.consentPdn?.message} />

          <Button type="submit" className="w-full" loading={registerMutation.isPending}>
            {t("auth.register.submit")}
          </Button>
        </form>
      </Card.Body>
      <Card.Footer className="mt-6 justify-center">
        <Link to="/auth/login" className="text-sm text-cta underline-offset-4 hover:underline">
          {t("auth.register.toLogin")}
        </Link>
      </Card.Footer>
    </Card>
  );
}
