# risks/ — Risk Register

Реестр активных рисков проекта. Каждый риск имеет ID (R-NN), severity, mitigation owner.

## Файлы

| Файл | Содержание |
|---|---|
| [`REGISTER.md`](./REGISTER.md) | Полный список R-01..R-29 с severity, mitigation, status |

## Когда читать

- При планировании phase — посмотреть R-NN, упомянутые в её phase-spec.
- При обнаружении нового риска — добавить запись в REGISTER.md.
- При смене severity / mitigation — обновить запись.

## Cross-references

- Top-5 active risks дублируются в [`../STATUS.md`](../STATUS.md) для быстрого обзора.
- ADR-025 определяет threshold для wave-перехода.
