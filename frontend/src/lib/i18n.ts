/**
 * i18n placeholder (Wave 0).
 *
 * Wave-0 ships hardcoded ru-RU copy. This thin `t()` indirection keeps call
 * sites i18n-shaped so Wave-1 can swap in a real library (i18next) without
 * touching components. Per phase-spec Task 11.
 *
 * // i18n-todo: replace the flat dictionary with a real i18n library (Wave 1+).
 */

const ru = {
  "common.appName": "Oriion",
  "common.tagline": "Твои личные AI-ассистенты",
  "common.loading": "Загрузка…",
  "common.retry": "Повторить",
  "common.cancel": "Отмена",
  "common.save": "Сохранить",
  "common.logout": "Выйти",
  "common.optional": "(необязательно)",
  "common.themeToggle": "Переключить тему",
  "common.skipToContent": "Перейти к содержимому",

  "auth.login.title": "Вход",
  "auth.login.submit": "Войти",
  "auth.login.toRegister": "Нет аккаунта? Зарегистрироваться",
  "auth.login.forgot": "Забыли пароль?",
  "auth.register.title": "Регистрация",
  "auth.register.submit": "Зарегистрироваться",
  "auth.register.toLogin": "Уже есть аккаунт? Войти",
  "auth.field.email": "Email",
  "auth.field.password": "Пароль",
  "auth.field.passwordConfirm": "Подтверждение пароля",
  "auth.field.displayName": "Имя",
  "auth.consent.pdn": "Согласен с обработкой персональных данных (ФЗ-152)",
  "auth.consent.marketing": "Хочу получать новости и материалы",

  "cells.title": "Ячейки",
  "cells.create": "Создать ячейку",
  "cells.createDisabled": "Доступно после Wave 1",
  "cells.empty.title": "Пока нет ячеек",
  "cells.empty.description": "Ячейка создаётся автоматически при регистрации.",
  "cells.col.name": "Название",
  "cells.col.template": "Шаблон",
  "cells.col.created": "Создана",
  "cells.detail.recentTasks": "Недавние задачи",
  "cells.detail.newTask": "Новая задача",

  "tasks.submit.title": "Постановка задачи",
  "tasks.submit.prompt": "Опишите задачу",
  "tasks.submit.preset": "Маркет-бриф",
  "tasks.submit.submit": "Создать задачу",
  "tasks.submit.costHint": "Ориентировочная стоимость: 1–50 T-кредитов",
  "tasks.result.tab.progress": "Прогресс",
  "tasks.result.tab.result": "Результат",
  "tasks.result.tab.cost": "Стоимость",
  "tasks.result.started": "Задача запущена",
  "tasks.result.completed": "Задача завершена",
  "tasks.result.region": "Итоговый ответ",
  "tasks.result.cancel": "Отменить задачу",
} as const;

export type I18nKey = keyof typeof ru;

/** Translate a key to ru-RU copy. Keys are type-checked, so always present. */
export function t(key: I18nKey): string {
  return ru[key];
}
