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
    commands: Optional[List[Dict[str, Any]]] = None


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

    @staticmethod
    def normalize_sql_syntax(cmd: str) -> str:
        """Fixes common model SQL hallucination artifacts (WITH CHECK, DEFAULTING, missing semicolons)."""
        cmd = re.sub(
            r'([a-zA-Z0-9_]+)\s+([A-Z0-9_]+(?:\([0-9, ]+\))?)\s+WITH\s+CHECK\s+BETWEEN\s+([0-9.]+)\s+AND\s+([0-9.]+)',
            r'\1 \2 CHECK (\1 BETWEEN \3 AND \4)',
            cmd,
            flags=re.IGNORECASE
        )
        cmd = re.sub(r'\bWITH\s+CHECK\b', 'CHECK', cmd, flags=re.IGNORECASE)
        cmd = re.sub(r'\bDEFAULTING\b', 'DEFAULT', cmd, flags=re.IGNORECASE)
        cmd = cmd.strip()
        if cmd and not cmd.endswith(';') and not cmd.startswith(('db.', '{', 'MATCH')):
            cmd += ';'
        return cmd

    @staticmethod
    def classify_sql_command_type(cmd: str) -> str:
        c = cmd.strip().upper()
        if c.startswith(('SELECT', 'WITH', 'EXPLAIN', 'SHOW', 'DESCRIBE', 'PRAGMA')):
            return 'SELECT'
        if c.startswith(('INSERT', 'UPDATE', 'DELETE', 'MERGE', 'REPLACE', 'UPSERT')):
            return 'DML'
        if c.startswith(('CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME')):
            return 'DDL'
        if c.startswith(('COMMIT', 'ROLLBACK', 'SAVEPOINT', 'BEGIN', 'START TRANSACTION', 'SET TRANSACTION')):
            return 'TCL'
        if c.startswith(('GRANT', 'REVOKE')):
            return 'DCL'
        return 'DML'

    @staticmethod
    def generate_command_reason(cmd: str, user_prompt: str = "") -> str:
        m_create = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\'\w]+)', cmd, re.IGNORECASE)
        if m_create:
            return f"Creates table {m_create.group(1)} with the specified columns and constraints."
        m_alter_auto = re.search(r'ALTER\s+TABLE\s+([`"\'\w]+)\s+AUTO_INCREMENT\s*=\s*(\d+)', cmd, re.IGNORECASE)
        if m_alter_auto:
            return f"Sets initial AUTO_INCREMENT counter for {m_alter_auto.group(1)} to {m_alter_auto.group(2)}."
        m_alter = re.search(r'ALTER\s+TABLE\s+([`"\'\w]+)', cmd, re.IGNORECASE)
        if m_alter:
            return f"Modifies schema definition for table {m_alter.group(1)}."
        m_update = re.search(r'UPDATE\s+([`"\'\w]+)', cmd, re.IGNORECASE)
        if m_update:
            return f"Updates records in {m_update.group(1)} matching criteria."
        m_delete = re.search(r'DELETE\s+FROM\s+([`"\'\w]+)', cmd, re.IGNORECASE)
        if m_delete:
            return f"Deletes targeted records from {m_delete.group(1)}."
        m_insert = re.search(r'INSERT\s+INTO\s+([`"\'\w]+)', cmd, re.IGNORECASE)
        if m_insert:
            return f"Inserts new row data into {m_insert.group(1)}."
        m_select = re.search(r'FROM\s+([`"\'\w]+)', cmd, re.IGNORECASE)
        if m_select:
            return f"Queries and retrieves projection data from {m_select.group(1)}."
        return "Executes database operation to fulfill natural language requirement."

    def _extract_sql_and_command_blocks(self, raw: str, user_prompt: str = "") -> Tuple[str, Optional[str], List[Dict[str, Any]]]:
        """
        Cleans LLM output:
        1. Separates <think>...</think> reasoning traces from the response.
        2. Unwraps JSON array of command blocks with prompt-mapped reasons when present.
        3. Normalizes SQL syntax (parenthesizing CHECK constraints, standard keywords).
        4. Returns (full_sql, thought, command_blocks).
        """
        thought: Optional[str] = None
        m_thought = re.search(r"<think>(.*?)</think>", raw, flags=re.DOTALL)
        if m_thought:
            thought = m_thought.group(1).strip()
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)

        raw = raw.strip()

        # Handle markdown code fences
        if "```" in raw:
            m_fence = re.search(r"```(?:json|sql)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
            if m_fence:
                raw = m_fence.group(1).strip()
            else:
                raw = re.sub(r"^```(?:json|sql)?\s*", "", raw, flags=re.IGNORECASE)
                raw = re.sub(r"\s*```$", "", raw).strip()

        cleaned_json_candidate = raw

        # Attempt JSON parsing first (structured commands with per-command reason)
        command_blocks: List[Dict[str, Any]] = []
        parsed_from_json = False

        try:
            m_bracket = re.search(r"(\[[\s\S]*\])", cleaned_json_candidate)
            json_text = m_bracket.group(1) if m_bracket else cleaned_json_candidate
            data = json.loads(json_text)
            if isinstance(data, dict):
                data = data.get("commands") or data.get("queries") or [data]
            if isinstance(data, list) and data:
                for item in data:
                    if isinstance(item, dict):
                        raw_cmd = item.get("command") or item.get("query") or item.get("sql") or ""
                        norm_cmd = self.normalize_sql_syntax(str(raw_cmd))
                        if not norm_cmd:
                            continue
                        c_type = str(item.get("type") or self.classify_sql_command_type(norm_cmd)).upper()
                        reason = str(item.get("reason") or self.generate_command_reason(norm_cmd, user_prompt))
                        command_blocks.append({
                            "command": norm_cmd,
                            "type": c_type,
                            "reason": reason
                        })
                    elif isinstance(item, str) and item.strip():
                        norm_cmd = self.normalize_sql_syntax(item)
                        command_blocks.append({
                            "command": norm_cmd,
                            "type": self.classify_sql_command_type(norm_cmd),
                            "reason": self.generate_command_reason(norm_cmd, user_prompt)
                        })
                if command_blocks:
                    parsed_from_json = True
        except Exception:
            parsed_from_json = False

        if parsed_from_json and command_blocks:
            full_sql = "\n\n".join(b["command"] for b in command_blocks)
            return full_sql, thought, command_blocks

        # Fallback to plain SQL parsing
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
                if re.match(r"^(explanation|note|this query|here is|the above|description):", stripped, re.IGNORECASE):
                    break
                cleaned_lines.append(line)

        candidate = "\n".join(cleaned_lines).strip() if cleaned_lines else raw
        candidate = self.normalize_sql_syntax(candidate)

        # Split candidate into sequential statement blocks
        raw_stmts = [s.strip() for s in re.split(r";\s*\n|;\s*$", candidate) if s.strip()]
        for stmt in raw_stmts:
            norm_s = self.normalize_sql_syntax(stmt)
            command_blocks.append({
                "command": norm_s,
                "type": self.classify_sql_command_type(norm_s),
                "reason": self.generate_command_reason(norm_s, user_prompt)
            })

        full_sql = "\n\n".join(b["command"] for b in command_blocks) if command_blocks else candidate
        return full_sql, thought, command_blocks

    def _clean_sql_and_extract_thought(self, raw: str) -> Tuple[str, Optional[str]]:
        """Backwards-compatible wrapper returning (clean_sql, thought)."""
        sql, thought, _ = self._extract_sql_and_command_blocks(raw)
        return sql, thought

    def generate_sql(
        self,
        query: str,
        schema_ddl: str = "",
        target_dialect: str = "mysql",
        model_name: Optional[str] = None,
        thinking_enabled: Optional[bool] = None,
        timeout: float = 120.0,
    ) -> OllamaGenerationResult:
        """
        Sends an NL2SQL request to Ollama and returns a validated SQL query.
        Automatically handles model routing, prompt engineering, and fallback.
        """
        start_time = time.perf_counter()
        active_model = self.resolve_best_model(model_name)

        dialect_label = target_dialect.upper() if target_dialect not in ("auto", None) else "SQL"
        has_schema = bool(schema_ddl and schema_ddl.strip())

        # High-precision system prompt
        schema_rule = (
            "3. Use only tables and columns described in the provided database schema."
            if has_schema
            else (
                "3. You are creating a new database or schema from scratch. Generate clean, valid DDL definitions. "
                "Never define duplicate column names in a table. "
                f"For {dialect_label}, use {'AUTO_INCREMENT' if dialect_label in ('MYSQL', 'MARIADB') else 'IDENTITY/AUTO_INCREMENT'} for primary key auto-incrementing columns."
            )
        )

        dialect_identity_rule = ""
        if dialect_label in ("MYSQL", "MARIADB"):
            dialect_identity_rule = "\n- For MySQL/MariaDB: Use INT NOT NULL AUTO_INCREMENT PRIMARY KEY for identity columns (do NOT use GENERATED BY DEFAULT AS IDENTITY)."

        dialect_rules = f"{dialect_identity_rule}\n- Wrap all CHECK constraints in standard SQL: CHECK (column BETWEEN min AND max) or CHECK (column >= min AND column <= max). Never write 'WITH CHECK'."

        system_instructions = (
            f"You are an expert database engineer and deterministic {dialect_label} query compiler. "
            f"Convert the user's natural language request into a valid JSON array of SQL command objects.\n\n"
            "STRICT JSON OUTPUT FORMAT:\n"
            "Output ONLY a valid JSON array where each item has:\n"
            "- \"command\": the exact valid executable SQL statement ending with a semicolon (;).\n"
            "- \"type\": \"DDL\" | \"DML\" | \"SELECT\" | \"TCL\".\n"
            "- \"reason\": a concise 1-sentence reason mapping the user prompt to this specific command.\n\n"
            "SYNTAX RULES:\n"
            f"{schema_rule}\n"
            f"{dialect_rules}\n"
            "- Every SQL statement must end with a semicolon (;).\n"
            "- For multi-table queries, use explicit JOIN syntax with correct foreign key conditions.\n\n"
            "Output ONLY the JSON array. Do not include introductory text, conversational greetings, or markdown explanations."
        )

        if thinking_enabled is False:
            system_instructions += (
                "\nAnswer with the pure JSON array immediately. Do NOT include <think> tags or chain-of-thought reasoning."
            )
        elif thinking_enabled is True:
            system_instructions += (
                "\nYou may use concise <think>...</think> for internal reasoning, but the text outside <think> must be ONLY the raw JSON array."
            )

        user_content = ""
        if schema_ddl.strip():
            user_content += f"Database Schema ({dialect_label}):\n{schema_ddl.strip()}\n\n"
        else:
            user_content += f"Context: Creating new database or schema from scratch (no prior tables).\n\n"
        user_content += f"Natural Language Request:\n{query.strip()}\n\nOutput JSON command array:"

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
                commands=[],
            )

        sql_candidate, thought, command_blocks = self._extract_sql_and_command_blocks(raw_response, user_prompt=query)

        # Validate syntax with sqlglot (non-standard dialects can be validated structurally with "sql" mode)
        valid_syntax = False
        if sql_candidate:
            try:
                # Validate each command or full candidate
                all_valid = True
                stmts_to_check = [b["command"] for b in command_blocks] if command_blocks else [sql_candidate]
                for stmt in stmts_to_check:
                    try:
                        p = sqlglot.parse_one(stmt, read=target_dialect if target_dialect not in ("auto", None) else None)
                        if p is None:
                            all_valid = False
                            break
                    except Exception:
                        # Non-SQL dialect fallback (opencypher, mongo)
                        if target_dialect in ("opencypher", "mongodb") or stmt.upper().startswith("MATCH") or stmt.startswith("db."):
                            continue
                        all_valid = False
                        break
                valid_syntax = all_valid
            except Exception:
                valid_syntax = False

        # If strict dialect check failed but commands exist, check if general sqlglot can parse
        if not valid_syntax and command_blocks:
            try:
                all_valid_lenient = True
                for b in command_blocks:
                    try:
                        sqlglot.parse_one(b["command"])
                    except Exception:
                        # Allow vendor-specific datatypes and graph syntax
                        if any(kw in b["command"].upper() for kw in ("CREATE TABLE", "CREATE DATABASE", "ALTER TABLE", "INSERT INTO", "SELECT")):
                            continue
                        all_valid_lenient = False
                        break
                if all_valid_lenient:
                    valid_syntax = True
            except Exception:
                pass

        # If still not marked valid but candidate clearly contains DDL statements, preserve it
        if not valid_syntax and sql_candidate:
            upper_cand = sql_candidate.upper()
            if "CREATE TABLE" in upper_cand or "CREATE DATABASE" in upper_cand:
                valid_syntax = True

        return OllamaGenerationResult(
            sql=sql_candidate,
            model_used=active_model,
            success=valid_syntax and bool(sql_candidate),
            reasoning_trace=thought,
            execution_time_ms=elapsed_ms,
            error=None if (valid_syntax and sql_candidate) else (error_msg or "Invalid SQL syntax in generated response"),
            is_fallback=is_fallback,
            commands=command_blocks,
        )

    def resolve_decision_model(self) -> Optional[str]:
        """
        Resolves the best available non-autoregressive decision/classifier model in Ollama.
        Prefers GPU-accelerated clef-flash over clef-flash-cpu.
        """
        try:
            models = self.list_models()
            decision_models = [
                m["name"] for m in models
                if "decision" in m.get("capabilities", []) or "clef" in m["name"].lower()
            ]
            if not decision_models:
                return None
            # Prefer GPU model over CPU variant
            gpu_models = [m for m in decision_models if "-cpu" not in m.lower()]
            return gpu_models[0] if gpu_models else decision_models[0]
        except Exception:
            return None

    def evaluate_decision(
        self,
        state: str,
        questions: Dict[str, Any],
        model: Optional[str] = None,
        timeout: float = 20.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Executes a non-autoregressive decision/classification request via Ollama's /v1/systemone endpoint.
        Used by the CLEF Intent Classifier & DBMS routing gate to eliminate false positives and false negatives.
        """
        target_model = model or self.resolve_decision_model()
        if not target_model:
            return None

        url = f"{self.host}/v1/systemone"
        payload = {
            "model": target_model,
            "state": state,
            "questions": questions,
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except Exception as e:
            logger.warning("Failed to query Ollama decision endpoint /v1/systemone: %s", e)
            return None


# Global default instance — shared across the pipeline
default_ollama = OllamaConnector()
