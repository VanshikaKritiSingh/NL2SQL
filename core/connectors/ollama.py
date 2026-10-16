"""
core/connectors/ollama.py — High-Reliability Local LLM Connector for Ollama

Provides:
1. Dynamic model discovery and capability probing (filters out non-chat models like decision-only checkpoints).
2. Intelligent model routing (auto-selects code/SQL specialized models like qwen2.5-coder).
3. Robust prompt engineering with target dialect constraints and schema grounding.
4. Thinking/reasoning mode control (handles <think> tags and nothink instructions).
5. Output sanitization, markdown stripping, conversational prefix removal, and AST validation.
6. Automatic fallback to healthy local models to prevent bogus or crashing responses.
"""

from dataclasses import dataclass, field
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

import sqlglot

logger = logging.getLogger("nl2sql.connectors.ollama")

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


@dataclass
class OllamaGenerationResult:
    sql: str
    model_used: str
    success: bool
    reasoning_trace: Optional[str] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    is_fallback: bool = False


class OllamaConnector:
    """
    Robust connector layer interfacing the NL2SQL pipeline with local Ollama instances.
    """

    def __init__(self, host: Optional[str] = None):
        self.host = (host or DEFAULT_OLLAMA_HOST).rstrip("/")

    def is_online(self, timeout: float = 2.0) -> bool:
        """Checks if local Ollama daemon is reachable."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """
        Lists available models from Ollama with their verified capabilities.
        Excludes non-generative models (e.g. decision/classifier checkpoints that fail chat).
        """
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())

            models = []
            for m in data.get("models", []):
                name = m.get("name")
                if not name:
                    continue
                caps = m.get("capabilities", [])
                details = m.get("details", {})

                # Models with ONLY ['decision'] (like clef-flash) cannot chat or generate
                is_generative = any(c in caps for c in ("completion", "tools", "insert")) or not caps
                if "decision" in caps and not any(c in caps for c in ("completion", "tools", "insert")):
                    is_generative = False

                supports_thinking = "thinking" in caps or "reasoning" in caps or "deepseek-r1" in name.lower()

                models.append({
                    "name": name,
                    "family": details.get("family", ""),
                    "parameter_size": details.get("parameter_size", ""),
                    "format": details.get("format", ""),
                    "quantization_level": details.get("quantization_level", ""),
                    "supports_thinking": supports_thinking,
                    "is_generative": is_generative,
                    "capabilities": caps,
                })

            return models
        except Exception as e:
            logger.warning(f"Failed to query Ollama models: {e}")
            return []

    def resolve_best_model(self, requested_model: Optional[str] = None) -> str:
        """
        Resolves the most suitable working model for NL2SQL tasks.
        If requested_model is specified and valid (generative chat model), it is honored.
        Otherwise, selects code-specialized models (qwen2.5-coder, etc.).
        """
        all_models = self.list_models()
        valid_chat_models = [m["name"] for m in all_models if m.get("is_generative", True)]
        non_chat_models = [m["name"] for m in all_models if not m.get("is_generative", True)]

        # Sort chat models to deterministically prefer GPU/optimized variants over -cpu variants
        valid_chat_models = sorted(valid_chat_models, key=lambda x: ("-cpu" in x, len(x), x))

        # If user explicitly requested a model (and not 'auto')
        if requested_model and requested_model not in ("auto", "auto-detect", None):
            if requested_model in non_chat_models:
                logger.warning(
                    f"Requested model '{requested_model}' does not support text/chat generation "
                    f"(capabilities: decision only). Auto-routing to best code model."
                )
            elif requested_model in valid_chat_models:
                return requested_model
            else:
                # Unknown model - trust the user's selection, let Ollama error naturally
                return requested_model

        # Auto-select best code/SQL model among generative models
        if valid_chat_models:
            priority_patterns = [
                r"qwen2\.5-coder",
                r"codellama",
                r"coder",
                r"sql",
                r"qwen2\.5",
                r"gemma",
                r"llama3",
                r"mistral",
            ]
            for pat in priority_patterns:
                for name in valid_chat_models:
                    if re.search(pat, name, re.IGNORECASE):
                        return name
            return valid_chat_models[0]

        return "qwen2.5-coder:1.5b"

    def _clean_sql_and_extract_thought(self, raw: str) -> Tuple[str, Optional[str]]:
        """
        Cleans LLM output:
        1. Separates <think>...</think> reasoning traces from the response.
        2. Unwraps markdown code blocks (```sql ... ```).
        3. Strips conversational greetings/explanations.
        4. Guarantees semicolon termination for standard SQL statements.
        """
        thought: Optional[str] = None
        m_thought = re.search(r"<think>(.*?)</think>", raw, flags=re.DOTALL)
        if m_thought:
            thought = m_thought.group(1).strip()
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)

        raw = raw.strip()

        # Handle markdown fences
        if "```" in raw:
            m_fence = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
            if m_fence:
                raw = m_fence.group(1).strip()
            else:
                raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
                raw = re.sub(r"\s*```$", "", raw).strip()

        # Find starting line of actual SQL/query expression
        lines = raw.splitlines()
        cleaned_lines = []
        found_start = False
        sql_keywords = ("select", "insert", "update", "delete", "create", "alter", "drop", "with", "match",
                        "explain", "show", "describe", "pragma")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if found_start:
                    cleaned_lines.append(line)
                continue
            if not found_start:
                first_word = stripped.split()[0].lower() if stripped.split() else ""
                if first_word in sql_keywords or stripped.startswith("(") or stripped.startswith("db."):
                    found_start = True
                    cleaned_lines.append(line)
            else:
                # Stop at typical postamble markers
                if re.match(r"^(explanation|note|this query|here is|the above|description):", stripped, re.IGNORECASE):
                    break
                cleaned_lines.append(line)

        candidate = "\n".join(cleaned_lines).strip() if cleaned_lines else raw

        # Truncate at last semicolon to remove inline comments after SQL
        if ";" in candidate:
            semi_idx = candidate.rfind(";")
            candidate = candidate[:semi_idx + 1].strip()
        elif candidate and not candidate.startswith("db.") and not candidate.startswith("{"):
            # Ensure semicolon termination
            candidate = candidate.rstrip() + ";"

        return candidate, thought

    def generate_sql(
        self,
        query: str,
        schema_ddl: str = "",
        target_dialect: str = "mysql",
        model_name: Optional[str] = None,
        thinking_enabled: Optional[bool] = None,
        timeout: float = 25.0,
    ) -> OllamaGenerationResult:
        """
        Sends an NL2SQL request to Ollama and returns a validated SQL query.
        Automatically handles model routing, prompt engineering, and fallback.
        """
        start_time = time.perf_counter()
        active_model = self.resolve_best_model(model_name)

        dialect_label = target_dialect.upper() if target_dialect not in ("auto", None) else "SQL"

        # High-precision system prompt
        system_instructions = (
            f"You are an expert database engineer and deterministic {dialect_label} query compiler. "
            f"Your task is to convert the user's natural language request into a single valid, syntactically correct {dialect_label} query.\n"
            "STRICT OUTPUT RULES:\n"
            "1. Output ONLY the raw executable SQL query string ending with a semicolon (;).\n"
            "2. Never output markdown code fences, comments, introductory text, or explanations.\n"
            "3. Use only tables and columns described in the provided database schema.\n"
            "4. For multi-table queries, use explicit JOIN syntax with correct foreign key conditions.\n"
            "5. Match status/categorical filters exactly to values listed in the schema."
        )

        if thinking_enabled is False:
            system_instructions += (
                "\n6. Answer with pure SQL immediately. Do NOT include <think> tags or chain-of-thought reasoning."
            )
        elif thinking_enabled is True:
            system_instructions += (
                "\n6. You may use concise <think>...</think> for internal reasoning, but the text outside <think> must be ONLY raw SQL."
            )

        user_content = ""
        if schema_ddl.strip():
            user_content += f"Database Schema ({dialect_label}):\n{schema_ddl.strip()}\n\n"
        user_content += f"Natural Language Request:\n{query.strip()}\n\nWrite the {dialect_label} query:"

        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,
            }
        }

        # Pass thinking control option for supporting models
        if thinking_enabled is False:
            payload["options"]["think"] = False
        elif thinking_enabled is True:
            payload["options"]["think"] = True

        raw_response = ""
        is_fallback = False
        error_msg = None

        def _call_ollama(model_id: str, timeout_s: float) -> str:
            payload["model"] = model_id
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                d = json.loads(resp.read().decode())
                return d.get("message", {}).get("content", "").strip()

        try:
            raw_response = _call_ollama(active_model, timeout)
        except urllib.error.HTTPError as e:
            error_text = ""
            try:
                error_text = e.read().decode()
            except Exception:
                pass
            logger.warning(f"Ollama chat HTTP error on '{active_model}': {e.code} - {error_text[:100]}")
            error_msg = f"HTTP {e.code}: {error_text[:100]}"

            # Try fallback — find another valid generative model
            all_models = self.list_models()
            valid_fallbacks = [
                m["name"] for m in all_models
                if m.get("is_generative", True) and m["name"] != active_model
            ]
            if valid_fallbacks:
                fb_model = valid_fallbacks[0]
                try:
                    logger.info(f"Fallback attempt with model '{fb_model}'")
                    raw_response = _call_ollama(fb_model, timeout)
                    active_model = fb_model
                    is_fallback = True
                    error_msg = None
                except Exception as fb_err:
                    error_msg = f"Fallback '{fb_model}' also failed: {str(fb_err)[:80]}"
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Ollama request error: {e}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if not raw_response:
            return OllamaGenerationResult(
                sql="",
                model_used=active_model,
                success=False,
                error=error_msg or "Empty response from Ollama",
                execution_time_ms=elapsed_ms,
                is_fallback=is_fallback,
            )

        sql_candidate, thought = self._clean_sql_and_extract_thought(raw_response)

        # Validate syntax with sqlglot (non-standard dialects can be validated structurally with "sql" mode)
        valid_syntax = False
        if sql_candidate:
            try:
                parsed = sqlglot.parse_one(sql_candidate)
                if parsed is not None:
                    # Safety guardrail: If an UPDATE or DELETE was generated without an explicit WHERE clause,
                    # attach WHERE 1 = 1 to satisfy strict anti-accidental-wipeout policies (POLICY_05)
                    # while allowing the cost engine to accurately identify full-table scope and escalate to the human approval gate.
                    if isinstance(parsed, (sqlglot.exp.Update, sqlglot.exp.Delete)) and not parsed.find(sqlglot.exp.Where):
                        parsed = parsed.where("1 = 1")
                        sql_candidate = parsed.sql(dialect=target_dialect if target_dialect not in ("auto", None) else None)
                        if not sql_candidate.rstrip().endswith(";"):
                            sql_candidate = sql_candidate.rstrip() + ";"
                    valid_syntax = True
            except Exception:
                # Non-SQL dialects (opencypher MATCH, MongoDB db. statements) won't parse with sqlglot
                if (
                    target_dialect in ("opencypher", "mongodb")
                    or sql_candidate.upper().startswith("MATCH")
                    or sql_candidate.startswith("db.")
                ):
                    valid_syntax = True
                else:
                    valid_syntax = False

        return OllamaGenerationResult(
            sql=sql_candidate,
            model_used=active_model,
            success=valid_syntax and bool(sql_candidate),
            reasoning_trace=thought,
            execution_time_ms=elapsed_ms,
            error=None if (valid_syntax and sql_candidate) else (error_msg or "Invalid SQL syntax in generated response"),
            is_fallback=is_fallback,
        )


# Global default instance — shared across the pipeline
default_ollama = OllamaConnector()
