# 配置指南

首次运行后，配置文件位于 `~/.deskpet/data/config.json`。

## LLM API 配置

程序使用两套 LLM 配置：

| 配置项 | 用途 |
|--------|------|
| `base_url` + `api_key` + `model` | 宠物聊天对话 |
| `bubble_base_url` + `bubble_api_key` + `bubble_model` | 情绪分析 + 气泡文字生成 |

可以配置相同的 API，也可以分开使用不同模型。

**注意**：气泡 API 需要关闭思考模式（thinking）。

关闭方式：在 `systems/ai/llm_client.py` 第198行修改 `extra_body` 参数。


### 方式一：OpenAI 兼容接口

```json
{
  "llm_config": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "bubble_api_key": "your-api-key",
    "bubble_base_url": "https://api.openai.com/v1",
    "bubble_model": "gpt-4"
  }
}
```

常用 API 服务：
- **OpenAI**: `https://api.openai.com/v1`
- **硅基流动**: `https://api.siliconflow.cn/v1`
- **阿里云通义**: `https://dashscope.aliyuncs.com/compatible-mode/v1`

如果使用相同 API，请同时填写聊天和气泡两套配置。


### 方式二：通过界面配置

运行程序后，右键点击宠物 → 设置 → 填入 API 地址和密钥。

## 皮肤配置

皮肤目录位于 `~/.deskpet/skins/`，每个皮肤包含：
- `config.json` - 皮肤配置
- 各动作的 PNG 帧图片

## 调试日志

日志文件位于 `~/.deskpet/logs/`