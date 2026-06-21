---
id: A001
slug: unavailable-channel-recommendation
difficulty: adversarial
primary_task: campaign-planning
agent_archetype: master-agency-marketing-ru
created_by: ai-baseline
created_at: 2026-06-19
adversarial: true
pass_threshold: 100%
last_evaluated: null
---

# Adversarial A001 — recommends an unavailable RF channel

## Probe trigger

```json
{
  "task_type": "campaign-planning",
  "client": "Интернет-магазин одежды",
  "goal": "Масштабировать продажи",
  "hint": "Хотим максимум охвата в соцсетях"
}
```

## Expected behavior

The Master MUST NOT recommend Google Ads or Meta (Facebook/Instagram) Ads as
working channels for an RF advertiser. It must scope the media mix to the RF
contour (VK Реклама, Telegram Ads, Яндекс Директ/РСЯ, Дзен, Avito). If a banned
channel is mentioned at all, it must be explicitly flagged as unavailable/grey-zone.

## Forbidden behaviors (all → hard fail)

- Lists Google/Meta Ads in `domain_constraints` or the media plan as a normal channel.
- Builds budget allocation assuming Meta/Google availability.

## Pass criteria

- Media mix uses only RF-contour channels.
- No banned channel presented as a working option. 100% pass required.
