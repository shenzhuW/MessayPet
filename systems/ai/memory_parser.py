# systems/ai/memory_parser.py
import re
import json
from typing import List, Dict, Optional, Tuple

class MemoryParser:
    MEMORY_PATTERN = r'<MEMORY>(.*?)</MEMORY>'
    UPDATE_PATTERN = r'<UPDATE>(.*?)</UPDATE>'
    DELETE_PATTERN = r'<DELETE>(.*?)</DELETE>'
    SUMMARIZE_PATTERN = r'<SUMMARIZE>(.*?)</SUMMARIZE>'

    def parse(self, text: str) -> Tuple[str, Optional[Dict]]:
        memories = []

        def extract_memory(match):
            try:
                data = json.loads(match.group(1))
                memories.append(data)
            except json.JSONDecodeError:
                pass
            return ""

        clean_text = re.sub(self.MEMORY_PATTERN, extract_memory, text, flags=re.DOTALL)
        clean_text = re.sub(self.UPDATE_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(self.DELETE_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(self.SUMMARIZE_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

        memory = memories[0] if memories else None
        return clean_text.strip(), memory

    def parse_extended(self, text: str) -> Tuple[str, List[Dict], List[Dict], Optional[str]]:
        memories = []
        updates = []
        summary = None

        for match in re.finditer(self.MEMORY_PATTERN, text, re.DOTALL):
            try:
                memories.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass

        for match in re.finditer(self.UPDATE_PATTERN, text, re.DOTALL):
            try:
                updates.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass

        sm = re.search(self.SUMMARIZE_PATTERN, text, re.DOTALL)
        if sm:
            summary = sm.group(1).strip()

        clean_text = text
        clean_text = re.sub(self.MEMORY_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(self.UPDATE_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(self.DELETE_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(self.SUMMARIZE_PATTERN, "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

        return clean_text.strip(), memories, updates, summary

    def extract_summary_request(self) -> str:
        return """如果对话历史较长，请总结要点，回复格式：
<SUMMARIZE>核心：...；用户特点：...；待续话题：...</SUMMARIZE>"""

    def extract_memory_instruction(self) -> str:
        return """请判断是否需要提取记忆。若是，在回复末尾添加：
<MEMORY>{"key": "描述", "value": "具体内容", "confidence": 0.8}</MEMORY>"""

    def extract_update_instruction(self) -> str:
        return """如果用户在对话中要求修改宠物设定或提供新信息，请输出：
<UPDATE>{"target": "pet_profile|user_profile|facts", "field": "字段名", "value": "新值"}</UPDATE>
<UPDATE>{"target": "user_profile", "field": "preferences", "add": "草莓"}</UPDATE>
<DELETE>{"target": "facts", "key": "旧事实"}</DELETE>"""