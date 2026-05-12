# ADR-006: Code-execution — Pyodide WASM (MVP) → gVisor (опционально) → Firecracker (Enterprise)

- **Status:** Accepted

## Decision

### Wave 2: Pyodide WASM в браузере

**Технология:** **Pyodide** (Python через WebAssembly), запускается в Web Worker в браузере клиента.

**Use case:** Analyst-роль в любом vertical-team может загрузить CSV, запустить pandas/numpy/matplotlib analysis, сгенерировать диаграмму/dataframe, результат — артефакт в S3.

**Детали:** см. [ADR-020](./ADR-020-pyodide-code-execution.md).

### Wave 3+ (опционально): Server-side gVisor sandbox

**Триггер активации:** customer demand на:
- Long-running analytical tasks (>30 сек)
- Tasks с external network (e.g. WB API через requests внутри sandbox)
- Generated artifacts >50 MB
- Dev team с code execution

**При активации:**
- gVisor + Docker на dedicated VM-пуле (2-3 VM × 4 vCPU)
- Strict seccomp + AppArmor + read-only rootfs + no-network-by-default
- Per-task isolation
- Pre-warmed container pool
- Cost-tracking: ~0.5 кр/мин CPU + ~0.1 кр/GB·hour RAM

### Wave 5+ (Enterprise): Firecracker microVMs

При Enterprise-клиентах с требованием hardware-level isolation:
- Firecracker microVMs на dedicated bare-metal hosts (Yandex Cloud BareMetal)
- Cold start <200ms
- Hardware-level boundary

## Consequences

- $0 backend infrastructure для code execution в Wave 2
- 0 risk утечки данных через sandbox в Wave 2 (всё в браузере клиента)
- Compliant с ФЗ-152 (ПДн в браузере клиента)
- Wave 3+ gVisor — путь для server-side execution когда понадобится

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-27](../risks/REGISTER.md), [R-28](../risks/REGISTER.md)
- Phase: 02.3 (Pyodide-runner для Analyst), 03.X+ (опц. gVisor)
- Related ADRs: ADR-020 (Pyodide deep-dive), ADR-017 (vertical-templates используют Analyst)
