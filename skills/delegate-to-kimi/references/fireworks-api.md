# Fireworks chat completions — reference

Only needed when `scripts/kimi.py` doesn't cover the case (multi-turn state,
tool calling, embeddings, batch jobs).

## Endpoint

```
POST https://api.fireworks.ai/inference/v1/chat/completions
Authorization: Bearer $FIREWORKS_API_KEY
Content-Type: application/json
```

The API is OpenAI-compatible, so the OpenAI SDKs work by pointing `base_url` at
`https://api.fireworks.ai/inference/v1`.

## Minimal call

```bash
curl -sS https://api.fireworks.ai/inference/v1/chat/completions \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "accounts/fireworks/models/kimi-k3",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 1024,
    "temperature": 0.6
  }'
```

## Parameters worth knowing

| Parameter          | Notes                                                                 |
| ------------------ | --------------------------------------------------------------------- |
| `model`            | Required, full path form: `accounts/<account>/models/<name>`.          |
| `messages`         | Required. `system` / `user` / `assistant` / `tool` roles.              |
| `max_tokens`       | Completion cap. `finish_reason: "length"` means it was truncated.      |
| `temperature`      | 0–2.                                                                   |
| `stream`           | SSE frames as `data: {...}`, terminated by `data: [DONE]`.             |
| `reasoning_effort` | `none` \| `low` \| `medium` \| `high` \| `max` on reasoning models.   |
| `thinking`         | Anthropic-style `{type, budget_tokens}` alternative to the above.      |
| `response_format`  | `{"type": "json_object"}` — also instruct JSON in the prompt itself.   |
| `tools`            | OpenAI-style function calling; Kimi K3 supports it.                    |

## Response shape

Non-streaming: `choices[0].message.content`, with reasoning models also setting
`choices[0].message.reasoning_content`, plus a `usage` object.

Streaming: `choices[0].delta.content` / `.reasoning_content` per frame.

## Kimi K3 facts

- Model id: `accounts/fireworks/models/kimi-k3`
- Routers: `accounts/fireworks/routers/kimi-k3-fast`, `.../kimi-k3-us`
- Context window: ~1M tokens (1040k)
- Pricing: $3.00 in / $0.30 cached in / $15.00 out per 1M tokens
- Function calling: supported

## Common errors

| Status | Meaning                                                        |
| ------ | -------------------------------------------------------------- |
| 401    | Bad or missing key.                                             |
| 404    | Model id typo, or model not available on serverless.            |
| 429    | Rate limited — back off, or move to a dedicated deployment.     |
| 400    | Usually `max_tokens` beyond the model's limit, or a bad field.  |
