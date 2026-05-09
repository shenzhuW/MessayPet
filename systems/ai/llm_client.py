from __future__ import annotations
import os
import asyncio
import httpx
import openai
import subprocess
import json
import uuid
import tempfile
from dataclasses import dataclass, field
from typing import Literal, List, Optional, AsyncIterator, Callable, Union

@dataclass
class Message:
    role: Literal["user", "assistant", "system"]
    content: str

    def to_dict(self):
        return {"role": self.role, "content": self.content}


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.messages: List[Message] = []
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=50.0, write=10.0, pool=5.0),
            headers={"Authorization": f"Bearer {config.api_key}"}
        )
        print(f"[LLM] Connected: {config.base_url}, Model: {config.model}")

    def add_message(self, role: Literal["user", "assistant"], content: str):
        self.messages.append(Message(role=role, content=content))
        if len(self.messages) > self.config.max_history:
            self.messages = self.messages[-self.config.max_history:]

    def clear_history(self):
        self.messages = []

    def get_context_messages(self) -> List[dict]:
        return [msg.to_dict() for msg in self.messages]

    async def chat(self, user_message: str) -> AsyncIterator[str]:
        self.add_message("user", user_message)

        if not self._client:
            yield "[AI client not configured]"
            return

        try:
            # vLLM 流式 API (OpenAI compatible)
            url = f"{self.config.base_url}/v1/chat/completions"
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": self.config.system_prompt},
                    *[msg.to_dict() for msg in self.messages]
                ],
                "stream": True,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # print(payload["messages"])

            # 确保 base_url 以 /v1 结尾
            base_url = self.config.base_url.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url += '/v1'
            url = f"{base_url}/chat/completions"

            finish_think = False

            async with self._client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                full_response = ""

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        # print("SSE data:", data)
                        if data == "[DONE]":
                            break
                        # 解析 SSE 数据
                        import json
                        try:
                            chunk = json.loads(data)
                            # print("Chunk:", chunk)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                if "<think>" in content:
                                    content = content.replace("<think>", "☁")
                                if "</think>" in content:
                                    content = content.replace("</think>", "☁")
                                full_response += content
                                yield content
                        except:
                            continue
                print("Full response:", full_response)
                self.add_message("assistant", full_response)
                finish_think = False
        except Exception as e:
            yield f"[Error: {str(e)}]"
            if self.messages and self.messages[-1].role == "user":
                self.messages.pop()

    async def chat_sync(self, user_message: str) -> str:
        result = []
        try:
            async for token in self.chat(user_message):
                result.append(token)
        except GeneratorExit:
            # 线程被中断，返回已收集的内容
            pass
        except asyncio.CancelledError:
            pass
        return "".join(result)

    async def chat_complete_async(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """非流式完整响应（异步版本）"""
        self.add_message("user", user_message)

        if not self._client:
            return "[AI client not configured]"

        try:
            # 确保 base_url 以 /v1 结尾
            base_url = self.config.base_url.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url += '/v1'
            url = f"{base_url}/chat/completions"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend([
                {"role": "system", "content": self.config.system_prompt},
                *[msg.to_dict() for msg in self.messages]
            ])

            payload = {
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            response = await self._client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            self.add_message("assistant", content)
            return content

        except Exception as e:
            error_msg = f"[Error: {str(e)}]"
            if self.messages and self.messages[-1].role == "user":
                self.messages.pop()
            return error_msg

    def chat_complete(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """非流式完整响应，用于气泡生成等需要等待完整回复的场景"""
        return self._chat_complete_sync(user_message, system_prompt)

    def _chat_complete_sync(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """同步请求（用于气泡显示，使用独立的 LLM API）"""
        self.add_message("user", user_message)

        # 气泡显示使用独立的 LLM API
        llm_base_url = self.config.bubble_base_url
        llm_api_key = self.config.bubble_api_key
        llm_model = self.config.bubble_model

        try:
            # 确保 base_url 以 /v1 结尾
            base_url = llm_base_url.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url += '/v1'

            client = openai.OpenAI(
                api_key=llm_api_key,
                base_url=base_url
            )

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=llm_model,
                messages=messages,
                extra_body={
                    "top_k": 20,
                    "chat_template_kwargs": {"enable_thinking": False}
                }
            )

            content = response.choices[0].message.content
            self.add_message("assistant", content)
            return content

        except Exception as e:
            error_msg = f"[Error: {str(e)}]"
            if self.messages and self.messages[-1].role == "user":
                self.messages.pop()
            return error_msg


class ClaudeCLIClient:
    """通过 Claude Code CLI 调用 AI（Windows 版本）"""

    # Windows Git Bash 路径
    GIT_BASH_PATH = r"W:\Git\Git\bin\bash.exe"

    def __init__(self, config: LLMConfig):
        self.config = config
        self.messages: List[Message] = []
        self._session_id = str(uuid.uuid4())

    def add_message(self, role: Literal["user", "assistant"], content: str):
        self.messages.append(Message(role=role, content=content))
        if len(self.messages) > self.config.max_history:
            self.messages = self.messages[-self.config.max_history:]

    def clear_history(self):
        self.messages = []
        self._session_id = str(uuid.uuid4())

    def _build_context(self) -> str:
        """构建上下文"""
        parts = [self.config.system_prompt, ""]
        for msg in self.messages[-self.config.max_history:]:
            role = "用户" if msg.role == "user" else "助手"
            parts.append(f"{role}: {msg.content}")
        return "\n".join(parts)

    async def chat(self, user_message: str) -> AsyncIterator[str]:
        """流式调用 Claude CLI"""
        self.add_message("user", user_message)

        context = self._build_context()
        prompt = context + "\n\n" + user_message

        # 构建命令
        prompt_escaped = prompt.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
        claude_cmd = f'claude -p --verbose --output-format stream-json --dangerously-skip-permissions --no-session-persistence "{prompt_escaped}"'

        # 设置环境变量
        env = os.environ.copy()
        env["CLAUDE_CODE_GIT_BASH_PATH"] = self.GIT_BASH_PATH
        env["ANTHROPIC_API_KEY"] = self.config.api_key

        cmd = [self.GIT_BASH_PATH, '-c', claude_cmd]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env
            )

            full_response = ""
            async for line in process.stdout:
                line_str = line.decode('utf-8', errors='replace').strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    msg_type = data.get("type", "")

                    # 解析 assistant 消息
                    if msg_type == "assistant":
                        message = data.get("message", {})
                        content = message.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if item.get("type") == "text":
                                    text = item.get("text", "")
                                    full_response += text
                                    yield text
                except json.JSONDecodeError:
                    continue

            await process.wait()

            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode('utf-8', errors='replace')
                yield f"[Claude CLI Error: {error_msg[:100]}]"
                if self.messages and self.messages[-1].role == "user":
                    self.messages.pop()
                return

            self.add_message("assistant", full_response)

        except FileNotFoundError:
            yield "[Error: Claude CLI 未安装或 Git Bash 路径不正确]"
        except Exception as e:
            yield f"[Error: {str(e)}]"

    def chat_sync(self, user_message: str) -> str:
        """同步版本"""
        loop = asyncio.new_event_loop()
        result = []
        async def collect():
            async for chunk in self.chat(user_message):
                result.append(chunk)
        try:
            loop.run_until_complete(collect())
        finally:
            loop.close()
        return "".join(result)


def create_llm_client(provider: str = "http") -> Union[LLMClient, ClaudeCLIClient]:
    """工厂函数：创建 LLM 客户端"""
    from core.config import get_llm_config
    config = get_llm_config()

    if provider == "claude-cli":
        return ClaudeCLIClient(config)

    return LLMClient(config)