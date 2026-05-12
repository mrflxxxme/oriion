# ADR-020: Pyodide WASM в браузере для code-execution (Analyst роль)

- **Status:** Accepted

## Decision

**Pyodide WASM** запускается в **Web Worker в браузере клиента** для всех Analyst-задач в Wave 2.

Use cases:
- WB/Ozon CSV отчёты → pandas analysis
- Yandex.Метрика / Google Analytics данные → визуализация
- Sales-pipeline (Bitrix24/amoCRM) → SQL-like queries
- Generated диаграмм для отчётов клиенту

### Implementation

```
frontend/src/features/pyodide-runner/
├── worker.ts                  # Web Worker запускает Pyodide
├── runner.ts                  # API между UI и worker
├── data-loader.ts             # CSV/JSON загрузка через File API
├── result-collector.ts        # output → backend через WebSocket
└── ui.tsx                     # Progress + result display
```

### Flow

```
1. Agent (DeepSeek-R1) генерирует Python-код для аналитики
2. Backend → frontend через WebSocket: {task_id, code, input_data_refs}
3. Frontend инициализирует Pyodide Web Worker (lazy-loaded ~30 MB)
4. Worker:
   - Загружает Pyodide runtime (CDN или self-hosted на нашем S3)
   - Pre-loads pandas, numpy, matplotlib, scipy, scikit-learn
   - Loads input data (CSV/JSON) из browser memory или File API
   - Executes generated Python code
   - Captures stdout, errors, generated charts (как base64 images)
5. Worker отправляет result в main thread
6. Main thread → backend через WebSocket: {task_id, status, stdout, artifacts}
7. Backend сохраняет artifacts в S3 + updates Task.status
```

### Pre-loaded packages в Pyodide build

- `pandas` (DataFrame, read_csv, read_excel)
- `numpy`
- `matplotlib` (без GUI backend, output как base64 PNG)
- `scipy`
- `scikit-learn`
- `beautifulsoup4`, `lxml`
- `openpyxl` (Excel files)
- Custom utility module `teamly_helpers` (наш Python pkg, упрощает CSV-parsing разных форматов: WB / Ozon / Yandex.Метрика / amoCRM exports)

### Ограничения Pyodide (что НЕ работает)

- ❌ Native C-extensions без Pyodide-port (например, `polars` не работает, но pandas работает)
- ❌ Network requests из Python (CORS-protected; backend pre-loads data перед передачей)
- ❌ Long-running >5 минут (browser-tab может закрыться)
- ❌ Heavy compute >2GB RAM (browser limit)
- ❌ Filesystem access (только virtual FS)

### Workarounds

- **Network data:** backend pre-loads через MCP-servers, передаёт в Pyodide как inline JSON/CSV
- **Long-running:** Wave 3+ опция «server-side execution» (gVisor) для больших jobs
- **Heavy compute:** UI flag «desktop recommended for heavy analysis» (R-28 mitigation)

### Browser compatibility

- Chrome 100+, Firefox 100+, Safari 16+, Edge 100+ (все Pyodide-supported)
- Mobile: работает, но slower (~3-5× медленнее desktop)
- IE/Old browsers: blocked с user-friendly upgrade message

### Performance characteristics

- Cold start: ~5-8 sec (Pyodide initial load)
- Hot start (subsequent tasks в той же session): <1 sec
- Pandas-heavy task (1MB CSV, 10 операций): ~3-5 sec
- ML training (sklearn, 10K rows): ~30-60 sec

### State persistence

- При закрытии browser-tab — Pyodide state теряется
- Generated artifacts всегда сохраняются на backend ДО displayed клиенту (через WebSocket-send в момент generation)
- При reconnect — task появляется в Task history с full result (из backend)

## Use cases по vertical-templates

### WB-Селлер team (Analyst)
- «Проанализируй продажи за месяц из этого CSV» → pandas group_by + диаграммы
- «Сравни конверсию топ-10 артикулов» → визуализация
- «Найди аномалии в остатках» → outlier detection

### Маркетинг-агентство (Analyst)
- «Проанализируй Yandex.Метрику этого клиента за неделю» → bounce rate / time-on-page summary
- «Сравни ROAS кампаний» → tabular comparison + chart

### Telegram-крейтор (Analyst)
- «Проанализируй engagement моего канала» → post-by-post ER calculation
- «Найди оптимальное время постинга» → heatmap

### ИП-Бухгалтерия (Analyst)
- «Проверь баланс по дебету/кредиту в этом CSV» → reconciliation
- (high-stakes — disclaimer mandatory)

### СМБ-Sales (Analyst)
- «Sales-funnel conversion analysis из CRM export» → funnel viz
- «Lead-quality score distribution» → histograms

## Wave 3+ opt-in: server-side gVisor

Если в Wave 3 customer demand появится:
- Workspace setting: «Server-side execution» (paid feature)
- Cost: +0.5 кр/мин CPU
- Use case: long-running ETL, ML training, jobs >5 минут

Если customer demand НЕ появится — server-side остаётся опцией Wave 4-5.

## Consequences

- $0 backend infrastructure для code-execution
- Полная изоляция данных — клиент-side execution, ПДн не покидает машину
- ФЗ-152 compliance упрощается
- Real-time visibility (клиент видит прогресс)

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-27](../risks/REGISTER.md), [R-28](../risks/REGISTER.md)
- Phase: 02.3 (Pyodide implementation)
- Related ADRs: ADR-006 (sandbox strategy), ADR-017 (vertical-templates use Analyst)
