/**
 * LoginPage — email/password sign-in wired to the live iam API.
 * Renders inside AuthShell's centered column (no extra <h1>).
 */
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button, Card, Checkbox, Input } from "@/components/ui";
import { t } from "@/lib/i18n";
import { loginSchema, type LoginValues } from "./schemas";
import { useLogin } from "./hooks";

export function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", remember: false },
  });

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = form;

  const remember = watch("remember") ?? false;

  const onValid = async (values: LoginValues): Promise<void> => {
    await login.mutateAsync({ email: values.email, password: values.password });
    await navigate({ to: "/cells" });
  };

  return (
    <Card variant="outlined" padding="lg">
      <Card.Header className="mb-6">
        <h2 className="text-xl font-semibold text-primary">{t("auth.login.title")}</h2>
      </Card.Header>
      <Card.Body>
        <form
          noValidate
          onSubmit={(e) => void handleSubmit(onValid)(e)}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <label htmlFor="login-email" className="text-sm font-medium text-primary">
              {t("auth.field.email")}
            </label>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? "login-email-error" : undefined}
              {...register("email")}
            />
            {errors.email ? (
              <p id="login-email-error" role="alert" className="text-xs text-danger-600">
                {errors.email.message}
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="login-password" className="text-sm font-medium text-primary">
              {t("auth.field.password")}
            </label>
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? "login-password-error" : undefined}
              {...register("password")}
            />
            {errors.password ? (
              <p id="login-password-error" role="alert" className="text-xs text-danger-600">
                {errors.password.message}
              </p>
            ) : null}
          </div>

          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-2">
              <Checkbox
                id="login-remember"
                checked={remember}
                onCheckedChange={(checked) => {
                  setValue("remember", checked === true);
                }}
              />
              <label
                htmlFor="login-remember"
                className="text-sm text-primary cursor-pointer select-none"
              >
                {t("auth.field.remember")}
              </label>
            </span>
            <a
              href="#"
              aria-disabled="true"
              className="text-sm text-cta underline-offset-4 hover:underline"
            >
              {t("auth.login.forgot")}
            </a>
          </div>

          <Button type="submit" className="w-full" loading={login.isPending}>
            {t("auth.login.submit")}
          </Button>
        </form>
      </Card.Body>
      <Card.Footer className="mt-6 justify-center">
        <Link to="/auth/register" className="text-sm text-cta underline-offset-4 hover:underline">
          {t("auth.login.toRegister")}
        </Link>
      </Card.Footer>
    </Card>
  );
}
