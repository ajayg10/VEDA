import os
import json
from openai import AsyncOpenAI
from pydantic import ValidationError
from shared.models import ExecutionPlan

PROVIDER_CONFIG = {
    "groq":   {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "LLM_API_KEY"},
    "ollama": {"base_url": "http://localhost:11434/v1",       "api_key_env": "LLM_API_KEY"},
}

SYSTEM_PROMPT = """
You are VEDA's Planner — an AI reasoning engine that converts natural language
goals into structured, executable workflow plans.

CRITICAL: Your ENTIRE response must be a single valid JSON object. No markdown,
no code fences, no explanation text before or after. Just the raw JSON object.

Available tools and their parameter schemas:
- shell_command  → {"command": "string"}
- file_create    → {"filename": "string", "content": "string"}
- file_read      → {"filename": "string"}
- http_request   → {"method": "GET|POST|PUT|DELETE", "url": "string", "headers": {}, "body": {}}
- python_script  → {"code": "string"}
  CRITICAL PYTHON RULE: ALL Python code MUST be in exactly ONE python_script step.
  NEVER use multiple python_script steps. NEVER split a Python program across steps.
  Variables do NOT persist between steps — a function defined in step 1 is GONE by step 2.
  If a goal requires Python, write the COMPLETE program in a single step.
  Wrong: step1=define function, step2=call function (BROKEN - function not visible in step2)
  Right: step1=complete program with definition AND call together (CORRECT)
  Use step_outputs[N] to read output from a prior http_request or shell_command step N.
- no_op          → {"note": "string"}

Required JSON structure:
{
  "goal": "string",
  "reasoning": "string",
  "steps": [
    {
      "step_id": 1,
      "description": "string",
      "tool": "shell_command | file_create | file_read | http_request | python_script | no_op",
      "parameters": {},
      "depends_on": [],
      "rationale": "string"
    }
  ],
  "estimated_complexity": "low | medium | high",
  "requires_confirmation": true | false
}

Rules:
- step_ids are sequential integers starting from 1.
- depends_on is a list of step_ids (integers), empty list [] if none.
- estimated_complexity must be exactly: low, medium, or high.
- requires_confirmation = true when any step deletes, overwrites, or sends data externally.
- Output ONLY the JSON object. Nothing else.
ENFORCEMENT: If you are about to create more than one python_script step, STOP and
combine them into one. A plan with two python_script steps is always wrong.
"""


class Planner:
    def __init__(self) -> None:
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        if provider not in PROVIDER_CONFIG:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Choose: {list(PROVIDER_CONFIG)}")
        cfg = PROVIDER_CONFIG[provider]
        self.client = AsyncOpenAI(
            api_key=os.getenv(cfg["api_key_env"], "placeholder"),
            base_url=cfg["base_url"],
        )
        self.model    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.provider = provider

    async def plan(
        self,
        user_goal:      str,
        memory_context: str = "",
        max_retries:    int = 2,
    ) -> ExecutionPlan:
        system_prompt = SYSTEM_PROMPT
        if memory_context:
            system_prompt = memory_context + "\n\n" + SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Goal: {user_goal}"},
        ]

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                raw: str = response.choices[0].message.content
                plan = ExecutionPlan.model_validate_json(raw)
                return plan

            except (ValidationError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({
                        "role": "user",
                        "content": f"Your response failed validation: {e}\nPlease fix the JSON and return ONLY the corrected object.",
                    })

        raise ValueError(f"Planner failed after {max_retries + 1} attempts. Last error: {last_error}")
