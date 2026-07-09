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
  "auth.field.remember": "Запомнить меня",

  "auth.error.emailInvalid": "Введите корректный email",
  "auth.error.passwordRequired": "Введите пароль",
  "auth.error.passwordTooShort": "Пароль должен содержать не менее 12 символов",
  "auth.error.passwordMismatch": "Пароли не совпадают",
  "auth.error.consentRequired": "Необходимо согласие на обработку персональных данных",

  "auth.strength.label": "Надёжность пароля",
  "auth.strength.weak": "Слабый",
  "auth.strength.medium": "Средний",
  "auth.strength.strong": "Надёжный",

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
  "cells.detail.tasksEmpty": "Пока нет задач",
  "cells.detail.metadata": "Метаданные",
  "cells.detail.slug": "Идентификатор",
  "cells.error.list": "Не удалось загрузить ячейки",
  "cells.error.detail": "Не удалось загрузить ячейку",
  "cells.dash": "—",

  "tasks.submit.title": "Постановка задачи",
  "tasks.submit.prompt": "Опишите задачу",
  "tasks.submit.preset": "Маркет-бриф",
  "tasks.submit.submit": "Создать задачу",
  "tasks.submit.costHint": "Ориентировочная стоимость: 1–50 T-кредитов",
  "tasks.submit.crumb": "Новая задача",
  "tasks.submit.promptHint":
    "Сформулируйте задачу в свободной форме — команда из трёх агентов выполнит её.",
  "tasks.submit.promptRequired": "Опишите задачу хотя бы одним символом.",
  "tasks.submit.promptTooLong": "Описание не должно превышать 4000 символов.",
  "tasks.submit.pipelineHint": "Над задачей работает конвейер из трёх агентов:",
  "tasks.submit.roleResearcher": "Исследователь",
  "tasks.submit.roleAnalyst": "Аналитик",
  "tasks.submit.roleWriter": "Райтер",
  "tasks.result.tab.progress": "Прогресс",
  "tasks.result.tab.result": "Результат",
  "tasks.result.tab.cost": "Стоимость",
  "tasks.result.started": "Задача запущена",
  "tasks.result.completed": "Задача завершена",
  "tasks.result.region": "Итоговый ответ",
  "tasks.result.cancel": "Отменить задачу",

  "memory.title": "Память",
  "memory.crumb": "Память",
  "memory.tab.cell": "Ячейка",
  "memory.tab.role": "Агент",

  "memory.role.agentLabel": "Агент",
  "memory.role.agentPlaceholder": "Выберите агента",
  "memory.role.agentFallbackPrefix": "Агент",
  "memory.role.noAgents.title": "Нет доступных агентов",
  "memory.role.noAgents.description": "В этой ячейке ещё не создано ни одного агента.",
  "memory.role.error.agents": "Не удалось загрузить список агентов",

  "memory.search.label": "Поиск по памяти",
  "memory.search.placeholder": "Что искать?",
  "memory.search.button": "Найти",
  "memory.search.clear": "Сбросить поиск",
  "memory.search.empty.title": "Ничего не найдено",

  "memory.add.toggle": "Добавить запись",
  "memory.add.titleLabel": "Заголовок",
  "memory.add.titlePlaceholder": "Необязательно",
  "memory.add.contentLabel": "Содержание",
  "memory.add.contentPlaceholder": "Что запомнить?",
  "memory.add.kindLabel": "Тип",
  "memory.add.piiLabel": "Содержит персональные данные",
  "memory.add.submit": "Запомнить",
  "memory.add.kindRequired": "Выберите тип записи.",
  "memory.add.titleTooLong": "Заголовок не должен превышать 200 символов.",
  "memory.add.contentRequired": "Введите содержание записи.",
  "memory.add.contentTooLong": "Содержание не должно превышать 8000 символов.",

  "memory.entry.deleteAction": "Удалить",
  "memory.entry.deleteConfirm.title": "Удалить запись из памяти?",
  "memory.entry.deleteConfirm.description": "Это действие нельзя отменить.",

  "memory.source.manual": "Вручную",
  "memory.source.filter_agent": "Фильтр-агент",
  "memory.source.summary": "Автосводка",

  "memory.kind.fact": "Факт",
  "memory.kind.note": "Заметка",
  "memory.kind.glossary": "Термин",
  "memory.kind.preference": "Предпочтение",
  "memory.kind.style": "Стиль",
  "memory.kind.process": "Процесс",

  "memory.empty.cell.title": "Пока нет ничего в памяти ячейки",
  "memory.empty.cell.description": "Добавьте первую запись вручную — команда будет её учитывать.",
  "memory.empty.role.title": "Пока нет ничего в памяти агента",
  "memory.empty.role.description": "Добавьте первую запись вручную — агент будет её учитывать.",
  "memory.error.list": "Не удалось загрузить память",

  "nav.dashboard": "Дашборд",

  "dashboard.title": "Дашборд",
  "dashboard.crumb": "Дашборд",

  "dashboard.balance.title": "Баланс кредитов",
  "dashboard.balance.available": "T-кредитов доступно",
  "dashboard.balance.periodUsage": "Использовано за период",
  "dashboard.balance.dailyUsage": "Использовано сегодня",
  "dashboard.balance.error": "Не удалось загрузить баланс",

  "dashboard.tasks.title": "Недавние задачи",
  "dashboard.tasks.empty.title": "Пока нет задач",
  "dashboard.tasks.empty.description":
    "Пройдите мастер настройки, чтобы поставить первую задачу команде агентов.",
  "dashboard.tasks.empty.action": "Начать мастер настройки",
  "dashboard.tasks.error": "Ошибка",
  "dashboard.tasks.col.title": "Задача",
  "dashboard.tasks.col.status": "Статус",
  "dashboard.tasks.col.created": "Создана",

  "dashboard.artifacts.title": "Артефакты",
  "dashboard.artifacts.empty.title": "Пока нет артефактов",
  "dashboard.artifacts.empty.description": "Артефакты появятся после выполнения задач.",
  "dashboard.artifacts.error": "Не удалось загрузить артефакты",
  "dashboard.artifacts.col.title": "Название",
  "dashboard.artifacts.col.type": "Тип",
  "dashboard.artifacts.col.updated": "Обновлён",

  "dashboard.memory.title": "Память команды",
  "dashboard.memory.description": "Посмотрите, что помнит команда и агенты.",
  "dashboard.memory.link": "Открыть память",

  "onboarding.crumb": "Мастер настройки",
  "onboarding.title": "Мастер настройки",
  "onboarding.skip": "Пропустить настройку",
  "onboarding.error.cell": "Не удалось загрузить вашу ячейку",

  "onboarding.stepBadge1": "Шаг 1 из 3",
  "onboarding.stepBadge2": "Шаг 2 из 3",
  "onboarding.stepBadge3": "Шаг 3 из 3",

  "onboarding.welcome.title": "Добро пожаловать в Oriion",
  "onboarding.welcome.description":
    "За 3 шага вы выберете команду AI-агентов и поставите ей первую задачу — результат появится на дашборде. Ячейка для команды уже создана автоматически.",
  "onboarding.welcome.next": "Далее",

  "onboarding.preset.title": "Выберите команду агентов",
  "onboarding.preset.description":
    "Пресет определяет, какие агенты будут работать над вашими задачами.",
  "onboarding.preset.back": "Назад",
  "onboarding.preset.next": "Продолжить",
  "onboarding.preset.error": "Не удалось подключить команду",

  "onboarding.preset.productivityCore.title": "Твои личные ассистенты",
  "onboarding.preset.productivityCore.description":
    "Координатор, Исследователь, Копирайтер и Аналитик — универсальная команда для любых задач.",
  "onboarding.preset.productivityCore.demoTitle": "Рыночный бриф для SMB",
  "onboarding.preset.productivityCore.demoPrompt":
    "Помоги подготовить короткий рыночный бриф: 3 тренда для малого бизнеса в РФ, 3 риска и 3 идеи для контента на ближайший месяц.",

  "onboarding.preset.agencyMarketingRu.title": "Маркетинговое агентство",
  "onboarding.preset.agencyMarketingRu.description":
    "Master-агент ведёт маркетинговую команду: бриф, конкурентный анализ, контент-план.",
  "onboarding.preset.agencyMarketingRu.demoTitle": "Маркетинговый пакет для нового продукта",
  "onboarding.preset.agencyMarketingRu.demoPrompt":
    "Подготовь маркетинговый пакет для нового SMB-продукта: краткий рыночный бриф, конкурентную матрицу (3 строки) и план на 3 поста для Telegram и vc.ru.",

  "onboarding.preset.telegramCreator.title": "Telegram-крейтор",
  "onboarding.preset.telegramCreator.description":
    "Master-агент и комьюнити-менеджер готовят контент-план и черновики постов для Telegram-канала.",
  "onboarding.preset.telegramCreator.demoTitle": "Контент-план Telegram-канала",
  "onboarding.preset.telegramCreator.demoPrompt":
    "Подготовь контент-план на 3 поста для Telegram-канала о продукте и черновик одного рекламного поста с учётом требований к маркировке рекламы.",

  "onboarding.task.title": "Поставьте первую задачу",
  "onboarding.task.description":
    "Мы подготовили демо-запрос для выбранной команды — можно отправить как есть или отредактировать.",
  "onboarding.task.prompt": "Описание задачи",
  "onboarding.task.submit": "Запустить задачу",
  "onboarding.task.back": "Назад",
  "onboarding.task.progressTitle": "Ход выполнения",
  "onboarding.task.toDashboard": "Перейти к дашборду",
} as const;

export type I18nKey = keyof typeof ru;

/** Translate a key to ru-RU copy. Keys are type-checked, so always present. */
export function t(key: I18nKey): string {
  return ru[key];
}
