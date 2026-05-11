#!/usr/bin/env python3
"""
Claude Code Hooks 通知脚本
"""
import json
import sys
import os
import re


def clean_text(text):
    """清理文本"""
    if not text:
        return ""
    try:
        text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    except:
        pass
    return ''.join(c for c in text if not (0xDC80 <= ord(c) <= 0xDCFF))


def get_transcript_messages(transcript_path):
    """从 transcript 文件获取用户输入和助手回复"""
    if not transcript_path:
        print("[Hook] No transcript path", file=sys.stderr)
        return None, None

    # 展开路径
    transcript_path = os.path.expanduser(transcript_path)
    print(f"[Hook] Transcript path: {transcript_path}", file=sys.stderr)

    if not os.path.exists(transcript_path):
        print(f"[Hook] Transcript not exists", file=sys.stderr)
        return None, None

    user_input = None
    assistant_reply = None

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"[Hook] Lines: {len(lines)}", file=sys.stderr)

        # 从后往前找最后的用户输入和助手回复
        for line in reversed(lines):
            try:
                entry = json.loads(line.strip())
                entry_type = entry.get('type', '')
                print(f"[Hook] Entry type: {entry_type}", file=sys.stderr)

                # 找助手回复
                if entry_type == 'assistant' and not assistant_reply:
                    msg = entry.get('message', {})
                    content = msg.get('content', [])
                    for block in content:
                        if block.get('type') == 'text':
                            assistant_reply = block.get('text', '')
                            break

                # 找用户输入
                if entry_type == 'user' and not user_input:
                    msg = entry.get('message', {})
                    content = msg.get('content', [])
                    for block in content:
                        if block.get('type') == 'text':
                            user_input = block.get('text', '')
                            break
                    if not user_input:
                        user_input = msg.get('text', '')

                if user_input and assistant_reply:
                    break
            except Exception as e:
                print(f"[Hook] Parse error: {e}", file=sys.stderr)
                continue

        print(f"[Hook] user_input: {user_input[:50] if user_input else None}", file=sys.stderr)
        print(f"[Hook] assistant_reply: {assistant_reply[:50] if assistant_reply else None}", file=sys.stderr)
        return user_input, assistant_reply
    except Exception as e:
        print(f"[Hook] Transcript error: {e}", file=sys.stderr)
        return None, None


def build_msg(hook: str, user_prompt: str, tool_name: str = "") -> tuple:
    """构建消息和状态类型

    Returns:
        tuple: (消息文本, 状态类型) 状态类型: "waiting", "complete", "normal"
    """
    if user_prompt and len(user_prompt) > 20:
        summary = user_prompt[:20] + "..."
    else:
        summary = user_prompt or "任务"

    if hook == "PermissionRequest":
        return (f"主人的「{summary}」在等待确认哦~", "waiting")
    elif hook == "Stop":
        return (f"「{summary}」完成啦~撒花~", "complete")
    else:
        return (f"Hook: {hook}", "normal")


def main():
    raw = sys.stdin.read()
    print(f"[Hook] Raw input: {raw[:100]}", file=sys.stderr)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[Hook] JSON error: {e}", file=sys.stderr)
        return

    hook = data.get("hook_event_name", "")
    print(f"[Hook] Event: {hook}", file=sys.stderr)

    if hook in ("Stop", "PermissionRequest", "UserPromptSubmit"):
        transcript_path = data.get("transcript_path", "")
        user_input, assistant_reply = get_transcript_messages(transcript_path)

        if user_input:
            user_input = clean_text(user_input)
            file_path = os.path.join(os.path.expanduser("~"), ".deskpet", "hook_user_prompt.txt")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(user_input[:200])

        if hook in ("Stop", "PermissionRequest"):
            msg, status = build_msg(hook, user_input or "")
            print(f"[Hook] Message: {msg}, Status: {status}", file=sys.stderr)

            notify_file = os.path.join(os.path.expanduser("~"), ".deskpet", "hook_notification.txt")
            os.makedirs(os.path.dirname(notify_file), exist_ok=True)
            # 格式: "状态|消息"
            with open(notify_file, "w", encoding="utf-8") as f:
                f.write(f"{status}|{msg}")


if __name__ == "__main__":
    main()