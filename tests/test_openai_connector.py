"""
tests/test_openai_connector.py — Test Suite for OpenAI-Compatible Provider & YAML Persistence
"""

import os
import tempfile
import yaml
import pytest

from core.connectors.openai_compatible import (
    OpenAICompatibleConnector,
    OpenAIGenerationResult,
)


def test_yaml_persistence_active_save_and_load():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        temp_path = tmp.name

    try:
        connector = OpenAICompatibleConnector(config_path=temp_path)
        assert connector.enabled is False
        assert connector.api_key == ""

        # Actively save credentials to YAML
        saved = connector.save_config(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test-secret-key-12345",
            model="deepseek-chat",
            models=["deepseek-chat", "deepseek-coder"],
            enabled=True,
            temperature=0.2,
            timeout=45.0,
        )

        assert saved["enabled"] is True
        assert saved["base_url"] == "https://api.deepseek.com/v1"
        assert saved["api_key"] == "sk-test-secret-key-12345"
        assert saved["model"] == "deepseek-chat"
        assert saved["models"] == ["deepseek-chat", "deepseek-coder"]

        # Verify YAML content on disk directly
        with open(temp_path, "r", encoding="utf-8") as f:
            disk_content = yaml.safe_load(f)

        assert "openai_compatible" in disk_content
        entry = disk_content["openai_compatible"]
        assert entry["enabled"] is True
        assert entry["base_url"] == "https://api.deepseek.com/v1"
        assert entry["api_key"] == "sk-test-secret-key-12345"
        assert entry["model"] == "deepseek-chat"
        assert entry["models"] == ["deepseek-chat", "deepseek-coder"]
        assert entry["temperature"] == 0.2
        assert entry["timeout"] == 45.0

        # Create a fresh connector instance pointing to the same YAML file
        fresh_connector = OpenAICompatibleConnector(config_path=temp_path)
        assert fresh_connector.is_configured() is True
        assert fresh_connector.api_key == "sk-test-secret-key-12345"
        assert fresh_connector.model == "deepseek-chat"
        assert fresh_connector.is_target_model("deepseek-chat") is True
        assert fresh_connector.is_target_model("deepseek-coder") is True
        assert fresh_connector.is_target_model("gpt-4o") is True  # standard prefix
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_sql_cleaning_and_safety_guardrails():
    connector = OpenAICompatibleConnector()

    # 1. Clean markdown fences and thoughts
    raw_output = """
<think>
Need to fetch all active users from users table ordered by date.
</think>
```sql
SELECT id, username, email FROM users WHERE status = 'active';
```
Here is your query.
"""
    sql, thought = connector._clean_sql_and_extract_thought(raw_output)
    assert sql == "SELECT id, username, email FROM users WHERE status = 'active';"
    assert thought == "Need to fetch all active users from users table ordered by date."

    # 2. Backtick stripping
    raw_backtick = "`SELECT * FROM orders WHERE amount > 100;`"
    sql2, _ = connector._clean_sql_and_extract_thought(raw_backtick)
    assert sql2 == "SELECT * FROM orders WHERE amount > 100;"

    # 3. Model target detection
    connector.enabled = True
    connector.api_key = "test"
    connector.models = ["gpt-4o", "my-custom-model"]
    assert connector.is_target_model("gpt-4o") is True
    assert connector.is_target_model("my-custom-model") is True
    assert connector.is_target_model("openai/my-model") is True
    assert connector.is_target_model("claude-3-5-sonnet") is True
    assert connector.is_target_model("unknown-local-llama") is False
