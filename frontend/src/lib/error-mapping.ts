/**
 * Backend error code → user-friendly Russian copy (phase-spec Task 12).
 *
 * The backend returns RFC 7807 problem+json with a `code` field
 * (e.g. `iam.auth.invalid_credentials`) and FastAPI 422 validation errors.
 * This maps the known codes; unknown codes fall back to a generic message.
 */

const messages: Record<string, string> = {
  "iam.auth.invalid_credentials": "Неверный email или пароль.",
  "iam.consent.pdn_missing": "Необходимо согласие на обработку персональных данных.",
  "iam.auth.email_in_use": "Этот email уже зарегистрирован.",
  "iam.auth.email_not_verified": "Email не подтверждён.",
  "iam.token.invalid": "Сессия истекла. Войдите снова.",
  "iam.rate_limited": "Слишком много попыток. Попробуйте позже.",
  "multitenancy.cell.not_found": "Ячейка не найдена.",
  "multitenancy.cell.slug_conflict": "Ячейка с таким идентификатором уже существует.",
  "tasks.not_found": "Задача не найдена.",
  "tasks.cannot_cancel": "Эту задачу нельзя отменить.",
};

const byStatus: Record<number, string> = {
  400: "Некорректный запрос.",
  401: "Требуется вход в систему.",
  403: "Недостаточно прав.",
  404: "Не найдено.",
  409: "Конфликт данных.",
  422: "Проверьте правильность заполнения полей.",
  429: "Слишком много запросов. Попробуйте позже.",
  500: "Внутренняя ошибка сервера. Попробуйте позже.",
  502: "Сервис временно недоступен.",
  503: "Сервис временно недоступен.",
};

/** Map a backend error `code` + HTTP status to Russian copy. */
export function mapErrorMessage(code: string | undefined, status: number): string {
  if (code && messages[code]) return messages[code];
  if (byStatus[status]) return byStatus[status];
  return "Что-то пошло не так. Попробуйте ещё раз.";
}
