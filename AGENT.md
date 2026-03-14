# Agent Documentation

## Overview

This agent is a Python CLI that connects to an LLM and answers questions using tools. It implements an **agentic loop** that allows multi-turn reasoning with tool calls. The agent can read documentation, explore source code, and query the backend API.

## Architecture

```
┌─────────────┐     ┌────────────────────────────────────────┐
│  CLI Input  │────▶│   agent.py with agentic loop           │
│  (question) │     │                                        │
└─────────────┘     │  1. Send question + tool schemas to LLM│
                    │  2. If tool_calls → execute tools      │
                    │  3. Feed results back to LLM           │
                    │  4. Repeat until final answer          │
                    │  5. Output JSON with answer + source   │
                    └────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Qwen Code API   │
                    │  (on VM)         │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Backend LMS API │
                    │  (via query_api) │
                    └──────────────────┘
```

## LLM Provider

**Provider:** Qwen Code API

**Deployment:** The Qwen Code API is deployed on a VM at `10.93.24.215:42005`.

**Model:** `qwen3-coder-plus`

**Why Qwen Code:**
- 1000 free requests per day
- Works from Russia without VPN
- No credit card required
- Supports OpenAI-compatible chat completions API with tool calling
- Strong tool calling capabilities

## Configuration

The agent reads configuration from environment variables:

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider API key |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Optional, default `http://localhost:42002` | Backend API base URL |

```bash
# .env.agent.secret
LLM_API_KEY=my-secret-qwen-key
LLM_API_BASE=http://10.93.24.215:42005/v1
LLM_MODEL=qwen3-coder-plus

# .env.docker.secret
LMS_API_KEY=set-it-to-something-and-remember-it
```

## Usage

```bash
# Run with a question
uv run agent.py "What does REST stand for?"

# Example output
{
  "answer": "Representational State Transfer.",
  "source": "wiki/rest-api.md",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/rest-api.md"}, "result": "..."}
  ]
}
```

## Output Format

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "<the LLM's response>",
  "source": "<file path that was used>",
  "tool_calls": [
    {
      "tool": "<tool_name>",
      "args": {"path": "..."},
      "result": "<tool output>"
    }
  ]
}
```

- `answer`: The LLM's text response
- `source`: File path that was used to find the answer (optional for system queries)
- `tool_calls`: Array of all tool calls made during the agentic loop

## Tools

### `read_file`

Read a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root

**Returns:** File contents as string (truncated to 10000 chars)

**Security:**
- Blocks `../` path traversal
- Blocks absolute paths
- Only allows files within project root

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root

**Returns:** Newline-separated listing of entries

**Security:**
- Blocks `../` path traversal
- Blocks absolute paths
- Only allows directories within project root

### `query_api`

Query the backend LMS API.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, etc.)
- `path` (string, required): API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests
- `authenticate` (boolean, optional): Whether to include auth header (default true)

**Returns:** JSON string with `status_code` and `body`

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret`

## Agentic Loop

The agent uses an agentic loop to answer questions:

1. **Send question to LLM** with tool schemas
2. **Check for tool calls:**
   - If yes → execute tools, append results to messages, go to step 1
   - If no → extract final answer, return JSON
3. **Maximum 10 iterations** to prevent infinite loops

```python
for iteration in range(MAX_ITERATIONS):
    response = call_llm(messages, tools)
    
    if response has tool_calls:
        for tool_call in tool_calls:
            result = execute_tool(tool_call)
            record tool call
        Append tool results to messages
        continue
    else:
        # Final answer
        return JSON output
```

## System Prompt

The system prompt guides the LLM to choose the right tool:

- **Wiki/documentation questions** → `list_files`, `read_file` on `wiki/`
- **Source code questions** → `read_file` directly on likely files (`backend/app/main.py`, `pyproject.toml`)
- **Data queries** (counts, analytics, status codes) → `query_api`
- **Bug diagnosis** → `query_api` to reproduce, then `read_file` to find bug
- **Unauthenticated access test** → `query_api` with `authenticate=false`

## Error Handling

- All debug/progress output goes to **stderr**
- Only valid JSON goes to **stdout**
- Exit code 0 on success
- Exit code 1 on failure (missing config, API error, timeout)

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI agent with agentic loop and tools |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `.env.docker.secret` | Backend API key (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `plans/task-3.md` | Task 3 implementation plan |
| `tests/test_agent.py` | Regression tests |
| `run_eval.py` | Evaluation benchmark script |

## Testing

```bash
# Run regression tests
uv run python tests/test_agent.py

# Run evaluation benchmark
uv run run_eval.py
```

### Test Questions

1. `"What is 2+2?"` → Basic LLM call
2. `"What files are in the wiki directory?"` → Uses `list_files`
3. `"How do you resolve a merge conflict in Git?"` → Uses `read_file`
4. `"How many items are in the database?"` → Uses `query_api`
5. `"What HTTP status code without auth?"` → Uses `query_api` with `authenticate=false`

## Benchmark Results

The evaluation benchmark (`run_eval.py`) tests 10 questions across all categories:

| # | Question Category | Tool Required | Status |
|---|-------------------|---------------|--------|
| 0 | Wiki: branch protection | `read_file` | ✓ |
| 1 | Wiki: SSH connection | `read_file` | ✓ |
| 2 | Source: Python framework | `read_file` | ✓ |
| 3 | Source: API routers | `list_files` | ✓ |
| 4 | Data: item count | `query_api` | ✓ |
| 5 | Data: status code | `query_api` | ✓ |
| 6 | Bug: ZeroDivisionError | `query_api`, `read_file` | ✓ |
| 7 | Bug: TypeError in analytics | `query_api`, `read_file` | ✓ |
| 8 | Reasoning: request lifecycle | `read_file` | ~ |
| 9 | Reasoning: ETL idempotency | `read_file` | ~ |

**Score: 8/10** (80% pass rate)

## Lessons Learned

1. **Tool descriptions matter**: The LLM needs clear, specific tool descriptions to choose the right tool. Adding examples like "For Python web framework questions, read: backend/app/main.py or pyproject.toml" significantly improved tool selection.

2. **Parameter naming is critical**: The LLM must use exact parameter names (`path` not `directory`). Inconsistent naming causes tool execution failures.

3. **Authentication flexibility**: Adding the `authenticate` parameter to `query_api` was essential for testing unauthenticated access and understanding API security behavior.

4. **Iteration limits**: The 10-iteration limit prevents infinite loops but can cut off complex multi-step reasoning. Most questions resolve in 2-4 iterations.

5. **Environment variable separation**: Keeping `LLM_API_KEY` (for Qwen) separate from `LMS_API_KEY` (for backend) is crucial. The autochecker injects different values, so hardcoding fails evaluation.

6. **Null handling**: The LLM sometimes returns `content: null` when making tool calls. Using `(msg.get("content") or "")` instead of `msg.get("content", "")` prevents `AttributeError`.

7. **Content truncation**: Very long files (>10000 chars) get truncated. This is usually sufficient but can miss details in large files like `docker-compose.yml` with extensive comments.

## Next Steps (Optional Task)

Potential improvements:
- Add `search_file` tool to search for text patterns across files
- Implement caching for repeated API calls
- Add retry logic for flaky API endpoints
- Improve source extraction with line numbers
- Add support for multi-file analysis in a single tool call
