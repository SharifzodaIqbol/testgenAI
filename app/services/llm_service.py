"""
LLM-сервис: взаимодействие с Groq API, управление промптами, парсинг ответов.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings
from app.db.base import TestCasePriority, TestCaseType

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


# ── Prompt templates ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ты — опытный QA-инженер и специалист по тест-дизайну.
Твоя задача — генерировать структурированные, детальные тест-кейсы на основе предоставленной документации.
Ты всегда отвечаешь строго в формате JSON, без лишних пояснений.
Каждый тест-кейс должен быть конкретным, воспроизводимым и независимым."""

USER_PROMPT_TEMPLATE = """
## Документация:
{doc_text}

## Задача:
Сгенерируй {num_cases} тест-кейсов на языке: {language}.
Типы тест-кейсов: {case_types}.
{focus_area_section}

## Требования к каждому тест-кейсу:
- Конкретные шаги (не менее 2, не более 10)
- Чёткое ожидаемое поведение для каждого шага
- Реалистичные тестовые данные
- Оценка confidence_score от 0.0 до 1.0 (насколько тест-кейс следует из документации)

## Формат ответа — строго JSON:
{{
  "test_cases": [
    {{
      "title": "Название тест-кейса",
      "description": "Краткое описание цели теста",
      "preconditions": "Что должно быть выполнено перед тестом",
      "steps": [
        {{"step": "Описание шага", "expected": "Ожидаемый результат шага"}}
      ],
      "expected_result": "Итоговый ожидаемый результат",
      "priority": "low|medium|high|critical",
      "case_type": "functional|negative|boundary|performance|security",
      "tags": ["тег1", "тег2"],
      "confidence_score": 0.95
    }}
  ]
}}
"""


def _build_user_prompt(
    doc_text: str,
    num_cases: int,
    case_types: list[TestCaseType],
    focus_area: str,
    language: str,
) -> str:
    focus_section = ""
    if focus_area:
        focus_section = f"\nФокус на области: {focus_area}\n"

    lang_name = "русском" if language == "ru" else "English"
    types_str = ", ".join(t.value for t in case_types)

    # Обрезаем документ если слишком длинный (Groq llama3-70b: 8192 токенов)
    max_doc_chars = 12_000
    if len(doc_text) > max_doc_chars:
        doc_text = doc_text[:max_doc_chars] + "\n\n[... документ обрезан ...]"

    return USER_PROMPT_TEMPLATE.format(
        doc_text=doc_text,
        num_cases=num_cases,
        language=lang_name,
        case_types=types_str,
        focus_area_section=focus_section,
    )


# ── Main LLM call ──────────────────────────────────────────────────────────────

async def generate_test_cases(
    doc_text: str,
    num_cases: int = 10,
    case_types: list[TestCaseType] | None = None,
    focus_area: str = "",
    language: str = "ru",
) -> dict[str, Any]:
    """
    Вызывает Groq API и возвращает структурированные тест-кейсы.
    Возвращает: {"test_cases": [...], "usage": {"prompt_tokens": N, "completion_tokens": N}}
    """
    if case_types is None:
        case_types = [TestCaseType.FUNCTIONAL, TestCaseType.NEGATIVE]

    user_prompt = _build_user_prompt(doc_text, num_cases, case_types, focus_area, language)

    payload = {
        "model": settings.GROQ_MODEL,
        "max_tokens": settings.GROQ_MAX_TOKENS,
        "temperature": settings.GROQ_TEMPERATURE,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(GROQ_BASE_URL, json=payload, headers=headers)
        resp.raise_for_status()

    data = resp.json()
    raw_content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    parsed = _parse_llm_response(raw_content)
    parsed["usage"] = {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
    }
    return parsed


def _parse_llm_response(raw: str) -> dict:
    """Парсит JSON из ответа LLM с обработкой edge-cases."""
    # Убираем markdown-блоки если есть
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON: %s | raw: %s", e, raw[:500])
        raise ValueError(f"LLM вернул невалидный JSON: {e}") from e

    test_cases = data.get("test_cases", [])
    if not isinstance(test_cases, list):
        raise ValueError("LLM ответ не содержит массив test_cases")

    # Нормализуем каждый тест-кейс
    normalized = []
    for tc in test_cases:
        normalized.append(_normalize_test_case(tc))

    return {"test_cases": normalized}


def _normalize_test_case(tc: dict) -> dict:
    """Применяем дефолты и валидируем поля тест-кейса."""
    valid_priorities = {p.value for p in TestCasePriority}
    valid_types = {t.value for t in TestCaseType}

    priority = tc.get("priority", "medium")
    if priority not in valid_priorities:
        priority = "medium"

    case_type = tc.get("case_type", "functional")
    if case_type not in valid_types:
        case_type = "functional"

    steps = tc.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    # Нормализуем шаги
    normalized_steps = []
    for s in steps:
        if isinstance(s, dict):
            normalized_steps.append({
                "step": str(s.get("step", "")),
                "expected": str(s.get("expected", "")),
            })
        elif isinstance(s, str):
            normalized_steps.append({"step": s, "expected": ""})

    confidence = float(tc.get("confidence_score", 0.8))
    confidence = max(0.0, min(1.0, confidence))

    return {
        "title": str(tc.get("title", "Без названия"))[:500],
        "description": str(tc.get("description", "")),
        "preconditions": str(tc.get("preconditions", "")),
        "steps": normalized_steps,
        "expected_result": str(tc.get("expected_result", "")),
        "priority": priority,
        "case_type": case_type,
        "tags": [str(t) for t in tc.get("tags", []) if t],
        "confidence_score": confidence,
    }
