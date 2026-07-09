"""Vertical review-artifacts runner — in-process Master plan+synthesis, real DeepSeek.

Produces the founder-facing review package data for a Wave-1 vertical by running
the pure LLM-contract path (no DB/Docker/API) that the live goldens exercise:

  - for each representative task: PLAN (deepseek-chat -> MasterPlan) then
    SYNTHESIS (deepseek-reasoner / R1 -> markdown), with the plan's real
    objective + constraints woven into the synthesis prompt;
  - the vertical's 5 adversarial probes (imported from the existing live-golden
    scripts) with their heuristic checks;
  - token + est. cost tracking.

Emits a single JSON document (full plans + full deliverables + probe results) to
--out, which the review-package markdown is assembled from.

Run:
  uv run --directory backend python scripts/review_artifacts_runner.py \
      --vertical telegram_creator --out /tmp/tg.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from uuid import uuid4

from src._shared.config import get_settings
from src.agents.master import (
    ROLE_KEY_PLAN,
    ROLE_KEY_SYNTHESIS,
    MasterDeps,
    MasterPlan,
    build_master_plan_agent,
    build_master_synthesis_agent,
)
from src.agents.services.role_prompt_loader import load_master_prompt
from src.llm_gateway.factory import build_llm_router
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

# Reuse the exact adversarial probe sets shipped with the live goldens.
from scripts.live_golden_master import _PROBES as _AGENCY_PROBES  # noqa: E402
from scripts.live_golden_telegram_creator import _PROBES as _TG_PROBES  # noqa: E402

# task = (task_id, title, user_prompt, source_label)
_AGENCY_TASKS: list[tuple[str, str, str, str]] = [
    (
        "AG-001",
        "Квартальный медиаплан для локальной сети кофеен (campaign-planning)",
        "Клиент — сеть кофеен, 4 точки, Казань. Цель — привлечь аудиторию 18-30 лет. "
        "Бюджет ~150 000 ₽/мес. Горизонт — квартал. Сделайте план продвижения.",
        "shipped golden task 001",
    ),
    (
        "AG-007",
        "Комплаенс-аудит рекламного текста для VK (compliance-audit, ФЗ-38)",
        "Проведите комплаенс-аудит рекламного объявления для VK. "
        "Текст объявления: «Лучший кофе в Казани! Дешевле всех конкурентов. Закажи сейчас.» "
        "Рекламодатель: ООО «Ромашка».",
        "shipped golden task 007",
    ),
    (
        "AG-R3",
        "Разбор эффективности рекламной кампании (performance reporting / KPI readout)",
        "Клиент — сервис доставки здорового питания в Екатеринбурге. За прошлый месяц "
        "потратили 200 000 ₽ на VK Рекламу и получили: 1 200 000 показов, 18 000 кликов, "
        "340 заявок, 95 оплаченных заказов, выручка 480 000 ₽. Сделайте разбор "
        "эффективности кампании и рекомендации на следующий месяц.",
        "representative (coverage-matrix: performance reporting)",
    ),
    (
        "AG-R4",
        "Конкурентный/рыночный анализ (competitor / market analysis)",
        "Клиент — сеть из 3 барбершопов в Нижнем Новгороде. Хотят понять, как "
        "конкуренты продвигаются в VK и Telegram, где у них слабые места и какие "
        "ниши/форматы свободны. Сделайте конкурентный анализ и рекомендации по "
        "позиционированию.",
        "representative (coverage-matrix: competitor analysis)",
    ),
    (
        "AG-R5",
        "Контент-воронка и креативные концепции (content funnel / creative)",
        "Клиент — онлайн-школа английского языка. Нужна контент-воронка для VK и "
        "Telegram: от прогрева холодной аудитории до заявки на пробный урок, с "
        "креативными концепциями под каждый этап. Бюджет на контент ограничен.",
        "representative (coverage-matrix: content funnel / creative concepts)",
    ),
]

_TG_TASKS: list[tuple[str, str, str, str]] = [
    (
        "TG-001",
        "Контент-план для нового кулинарного канала (content-plan)",
        "Хочу запустить Telegram-канал про домашнюю кулинарию — простые рецепты "
        "после работы. Канал ещё не создан, веду один, опыта ведения нет. Сделай "
        "контент-план на месяц.",
        "shipped golden task 001",
    ),
    (
        "TG-008",
        "Пост-кейс по фактам клиента (post-drafting)",
        "Ниша — маркетинг для малого бизнеса, рубрика «кейс среды». Факты: клиент — "
        "локальная кофейня, за 2 месяца таргета в VK заявки на кейтеринг выросли на "
        "40%. Напиши пост-кейс, тон — конкретика, без воды.",
        "shipped golden task 008",
    ),
    (
        "TG-015",
        "Диагностика месячного спада вовлечённости (channel-audit)",
        "Канал 42 000 подписчиков. За последние 4 недели ERR падает: 9%, 8%, 6%, "
        "4.5%. Мы перешли с 3 постов в неделю на 6, чтобы расти быстрее. Что "
        "происходит и что делать?",
        "shipped golden task 015",
    ),
    (
        "TG-022",
        "Проверка готовности к РКН-реестру блогеров (compliance-audit)",
        "У нас растёт канал: 1 июня было 9200 подписчиков, 20 июня — 10150, 8 июля — "
        "10800. Нужно ли нам что-то делать по закону из-за роста подписчиков?",
        "shipped golden task 022",
    ),
    (
        "TG-029",
        "Платная подписка Stars vs. полноценный курс (monetization)",
        "Канал про иллюстрацию и цифровой арт, 60 000 подписчиков, команда 2 "
        "человека. Запускать платную подписку в Stars на эксклюзивный контент или "
        "делать полноценный курс по иллюстрации?",
        "shipped golden task 029",
    ),
]

_CONFIG: dict[str, dict[str, Any]] = {
    "agency_marketing_ru": {"tasks": _AGENCY_TASKS, "probes": _AGENCY_PROBES},
    "telegram_creator": {"tasks": _TG_TASKS, "probes": _TG_PROBES},
}


def _usage(run: Any) -> tuple[int, int]:
    attr = getattr(run, "usage", None)
    u = attr() if callable(attr) else attr
    if u is None:
        return 0, 0
    i = getattr(u, "input_tokens", None) or getattr(u, "request_tokens", None) or 0
    o = getattr(u, "output_tokens", None) or getattr(u, "response_tokens", None) or 0
    return int(i), int(o)


def _plan_text(plan: MasterPlan) -> str:
    parts = [plan.objective, plan.rationale, *plan.domain_constraints, *plan.success_criteria]
    return " \n ".join(parts).lower()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vertical", required=True, choices=list(_CONFIG))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    settings = get_settings()
    if not settings.deepseek_api_key.get_secret_value():
        print("FAIL: DEEPSEEK_API_KEY not set — cannot run.")
        return 2

    cfg = _CONFIG[args.vertical]
    bundle = build_llm_router(settings)
    router = bundle.router
    prompt = load_master_prompt(args.vertical)
    deps = MasterDeps(
        cell_id=uuid4(), task_id=uuid4(), user_id=uuid4(), vertical_tag=args.vertical
    )

    plan_model = LLMGatewayModel(role_key=ROLE_KEY_PLAN, llm_router=router)
    plan_agent = build_master_plan_agent(model=plan_model, master_prompt=prompt)
    synth_model = LLMGatewayModel(role_key=ROLE_KEY_SYNTHESIS, llm_router=router)
    synth_agent = build_master_synthesis_agent(model=synth_model, master_prompt=prompt)

    tok_in = tok_out = 0
    out: dict[str, Any] = {"vertical": args.vertical, "tasks": [], "adversarial": []}

    for task_id, title, user_prompt, source in cfg["tasks"]:
        print(f"=== {task_id} PLAN ===", flush=True)
        plan_run = await plan_agent.run(user_prompt, deps=deps)
        plan: MasterPlan = plan_run.output
        pi, po = _usage(plan_run)
        tok_in += pi
        tok_out += po

        constraints = "\n".join(f"- {c}" for c in plan.domain_constraints)
        criteria = "\n".join(f"- {c}" for c in plan.success_criteria)
        synth_prompt = (
            f"Ты — Master-Agent вертикали. Команда проработала задачу пользователя; "
            f"синтезируй финальный deliverable — чистый markdown, готовый к выдаче "
            f"клиенту/автору (без служебных комментариев).\n\n"
            f"Стратегическая цель (objective): {plan.objective}\n\n"
            f"Ключевые доменные ограничения:\n{constraints}\n\n"
            f"Критерии успеха:\n{criteria}\n\n"
            f"Исходный запрос пользователя: {user_prompt}"
        )
        print(f"=== {task_id} SYNTH ===", flush=True)
        synth_run = await synth_agent.run(synth_prompt, deps=deps)
        synth_text = str(synth_run.output)
        si, so = _usage(synth_run)
        tok_in += si
        tok_out += so

        out["tasks"].append(
            {
                "task_id": task_id,
                "title": title,
                "source": source,
                "user_prompt": user_prompt,
                "plan": {
                    "objective": plan.objective,
                    "rationale": plan.rationale,
                    "domain_constraints": list(plan.domain_constraints),
                    "success_criteria": list(plan.success_criteria),
                },
                "synthesis_markdown": synth_text,
                "plan_ok": bool(plan.objective.strip())
                and len(plan.domain_constraints) >= 1
                and len(plan.success_criteria) >= 1,
                "synth_ok": len(synth_text.strip()) > 200,
                "tokens": {"in": pi + si, "out": po + so},
            }
        )

    for slug, trigger, check in cfg["probes"]:
        print(f"=== probe {slug} ===", flush=True)
        run = await plan_agent.run(trigger, deps=deps)
        p = run.output
        ai, ao = _usage(run)
        tok_in += ai
        tok_out += ao
        if isinstance(p, MasterPlan):
            ok, note = check(_plan_text(p))
        else:
            ok, note = False, "did not return MasterPlan"
        out["adversarial"].append(
            {"slug": slug, "trigger": trigger, "ok": bool(ok), "note": note}
        )

    cost = tok_in * 0.27e-6 + tok_out * 1.10e-6
    out["tokens_in"] = tok_in
    out["tokens_out"] = tok_out
    out["cost_usd"] = round(cost, 4)
    out["provider_model_plan"] = f"{plan_model._last_provider_slug}/{plan_model._last_model_name}"
    out["provider_model_synth"] = (
        f"{synth_model._last_provider_slug}/{synth_model._last_model_name}"
    )

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    adv_pass = sum(1 for a in out["adversarial"] if a["ok"])
    print(
        f"\nDONE {args.vertical}: tasks={len(out['tasks'])} "
        f"adversarial={adv_pass}/{len(out['adversarial'])} "
        f"tokens in={tok_in} out={tok_out} cost=${cost:.4f} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
