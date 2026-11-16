import json
import logging
from typing import List, Dict, Any, Optional
import ollama
from nova.config import MODEL_NAME, OLLAMA_HOST

logger = logging.getLogger("nova.brain.llm")

class NovaBrain:
    """Wrapper around Ollama client with tool calling and fallback parsing."""

    def __init__(self, model_name: str = MODEL_NAME, host: str = OLLAMA_HOST):
        self.model_name = model_name
        self.host = host
        self.client = ollama.Client(host=self.host)

    def is_connected(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            self.client.list()
            return True
        except Exception as e:
            logger.debug(f"Ollama connection check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """List locally pulled models in Ollama."""
        try:
            res = self.client.list()
            # res['models'] or res.models
            models_list = getattr(res, "models", None) or res.get("models", [])
            names = []
            for m in models_list:
                name = getattr(m, "model", None) or m.get("name") or m.get("model")
                if name:
                    names.append(name)
            return names
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Sends messages and optional tools to Ollama.
        Returns a dict with:
        - content: str
        - tool_calls: list of dicts [{'name': ..., 'arguments': ...}]
        """
        kwargs = {
            "model": self.model_name,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = self.client.chat(**kwargs)
            message = response.message
            content = message.content or ""
            raw_tool_calls = getattr(message, "tool_calls", None)

            parsed_tool_calls = []
            if raw_tool_calls:
                for tc in raw_tool_calls:
                    fn = getattr(tc, "function", None) or tc.get("function", {})
                    name = getattr(fn, "name", None) or fn.get("name")
                    args = getattr(fn, "arguments", None) or fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            pass
                    if name:
                        parsed_tool_calls.append({"name": name, "arguments": args})

            # Fallback JSON parsing if no native tool calls but content contains a tool call block
            if not parsed_tool_calls and "```json" in content:
                parsed_tool_calls = self._extract_json_tool_calls(content)

            return {
                "content": content,
                "tool_calls": parsed_tool_calls,
                "raw": response
            }
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise e

    def _extract_json_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Fallback tool extractor for models that emit tool calls as JSON code blocks."""
        calls = []
        try:
            start_marker = "```json"
            end_marker = "```"
            idx = 0
            while True:
                start = text.find(start_marker, idx)
                if start == -1:
                    break
                end = text.find(end_marker, start + len(start_marker))
                if end == -1:
                    break
                block = text[start + len(start_marker):end].strip()
                idx = end + len(end_marker)
                data = json.loads(block)
                if isinstance(data, dict) and ("name" in data or "tool" in data):
                    name = data.get("name") or data.get("tool")
                    args = data.get("arguments") or data.get("parameters") or {}
                    calls.append({"name": name, "arguments": args})
        except Exception as e:
            logger.debug(f"JSON tool call fallback extraction failed: {e}")
        return calls
