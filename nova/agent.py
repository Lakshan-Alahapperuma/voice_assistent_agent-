import uuid
import json
import logging
from typing import Optional, Dict, Any, List
from nova.config import MODEL_NAME, AUTO_CONFIRM_SAFE
from nova.brain.prompts import SYSTEM_PROMPT
from nova.brain.memory import NovaMemory
from nova.brain.llm import NovaBrain
from nova.tools import create_default_registry, ToolRegistry
from nova.safety.guardrails import SafetyGuardrail
from nova.voice.tts import MacTTS
from nova.voice.stt import WhisperSTT
from nova.voice.wakeword import WakeWordDetector

logger = logging.getLogger("nova.agent")

class NovaAgent:
    """Core autonomous agent orchestrator for Nova."""

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        enable_voice: bool = False,
        auto_confirm: bool = AUTO_CONFIRM_SAFE,
        session_id: Optional[str] = None
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.brain = NovaBrain(model_name=model_name)
        self.memory = NovaMemory()
        self.registry: ToolRegistry = create_default_registry()
        self.safety = SafetyGuardrail(auto_confirm=auto_confirm)
        self.tts = MacTTS()
        self.stt = WhisperSTT()
        self.wakeword = WakeWordDetector()
        self.enable_voice = enable_voice

    def run_turn(self, user_text: str) -> str:
        """Processes a single conversational turn with tool execution loop."""
        user_text = user_text.strip()
        if not user_text:
            return ""

        # Save user message to persistent SQLite memory
        self.memory.add_message(self.session_id, "user", user_text)

        # Retrieve recent conversation context
        history = self.memory.get_recent_messages(self.session_id, limit=12)

        # Build prompt list with system instructions
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})

        tools_schema = self.registry.get_ollama_tools()

        # Call Ollama
        try:
            response = self.brain.chat(messages, tools=tools_schema)
        except Exception as e:
            err_msg = f"Sorry, I had trouble connecting to the local AI brain: {str(e)}"
            if self.enable_voice:
                self.tts.speak(err_msg)
            return err_msg

        content = response["content"]
        tool_calls = response["tool_calls"]

        # If tools were invoked
        if tool_calls:
            messages.append({"role": "assistant", "content": content or "Executing actions..."})

            for tc in tool_calls:
                tool_name = tc["name"]
                args = tc["arguments"]
                tool = self.registry.get_tool(tool_name)

                # Check safety approval
                if tool and tool.requires_confirmation:
                    approved = self.safety.request_approval(tool_name, args)
                    if not approved:
                        result = {
                            "status": "cancelled",
                            "message": f"User cancelled execution of {tool_name}."
                        }
                        self.memory.log_task(tool_name, args, str(result), status="cancelled", task_description=user_text)
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(result)
                        })
                        continue

                # Execute approved tool
                result = self.registry.execute(tool_name, args)
                status = "error" if isinstance(result, dict) and "error" in result else "success"
                self.memory.log_task(tool_name, args, str(result), status=status, task_description=user_text)

                messages.append({
                    "role": "tool",
                    "content": json.dumps(result)
                })

            # Call brain again with tool outputs for final synthesis
            try:
                final_res = self.brain.chat(messages)
                final_answer = final_res["content"]
            except Exception as e:
                final_answer = f"Actions executed, but error occurred synthesizing summary: {str(e)}"
        else:
            final_answer = content

        # Save assistant answer to memory
        self.memory.add_message(self.session_id, "assistant", final_answer)

        # Spoken response if voice is enabled
        if self.enable_voice and final_answer:
            self.tts.speak(final_answer, async_mode=True)

        return final_answer
