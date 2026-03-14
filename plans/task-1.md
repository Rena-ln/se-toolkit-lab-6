# Task 1 Plan: Call an LLM from Code

## LLM Provider

**Provider:** Qwen Code API (deployed on VM)

**Configuration:**
- `LLM_API_BASE`: `http://10.93.24.215:42005/v1`
- `LLM_API_KEY`: `my-secret-qwen-key` (stored in `.env.agent.secret`)
- `LLM_MODEL`: `qwen3-coder-plus`

**Why Qwen Code:**
- 1000 free requests per day
- Works from Russia without VPN
- No credit card required
- Supports OpenAI-compatible chat completions API
- Strong tool calling capabilities (will be used in Task 2-3)

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  CLI Input  │────▶│   agent.py       │────▶│  Qwen Code API  │
│  (question) │     │  (Python CLI)    │     │  (on VM)        │
└─────────────┘     └──────────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │  JSON Output     │
                    │  {answer,        │
                    │   tool_calls}    │
                    └──────────────────┘
```

## Implementation Steps

1. **Read environment variables** from `.env.agent.secret`:
   - `LLM_API_KEY`
   - `LLM_API_BASE`
   - `LLM_MODEL`

2. **Parse command-line argument** (question) using `sys.argv`

3. **Call LLM API** using `requests` library:
   - POST to `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Body: `{"model": LLM_MODEL, "messages": [{"role": "user", "content": question}]}`

4. **Parse response** and extract answer from `choices[0].message.content`

5. **Output JSON** to stdout:
   ```json
   {"answer": "<llm_response>", "tool_calls": []}
   ```

6. **Error handling**:
   - Log errors to stderr
   - Exit with code 1 on failure

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main CLI agent
├── .env.agent.secret     # LLM credentials (gitignored)
├── AGENT.md              # Documentation
├── plans/
│   └── task-1.md         # This plan
└── tests/
    └── test_agent.py     # Regression test
```

## Testing

- Run `uv run agent.py "What is 2+2?"` 
- Verify JSON output has `answer` and `tool_calls` fields
- Test with different questions
- Verify exit code is 0 on success

## Next Steps (Task 2-3)

After Task 1 is complete:
- Add tools: `read_file()`, `list_files()`, `query_api()`
- Implement agentic loop
- Add system prompt with domain knowledge
