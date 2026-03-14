# Task 3 Plan: The System Agent

## Overview

Task 3 extends the agent from Task 2 with:
1. A new tool: `query_api` to query the backend LMS API
2. Updated system prompt to distinguish between wiki lookups and system queries
3. Environment variable handling for API configuration
4. Benchmark evaluation with `run_eval.py`

## New Tool: `query_api`

**Description:** Call the backend LMS API to get system data.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, etc.)
- `path` (string, required): API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body`

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret`

**Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the backend LMS API. Use for data-dependent questions like item counts, analytics, or status codes.",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method: GET, POST, etc."
        },
        "path": {
          "type": "string",
          "description": "API path, e.g., '/items/', '/analytics/completion-rate'"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

## Environment Variables

The agent must read these from environment:

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider API key |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Optional, default `http://localhost:42002` | Backend API base URL |

## System Prompt Update

The system prompt should guide the LLM to choose the right tool:

- **Wiki questions** (how to, documentation) → `list_files`, `read_file`
- **System facts** (framework, ports, status codes) → `query_api` or `read_file` on source code
- **Data queries** (item count, scores, analytics) → `query_api`
- **Bug diagnosis** → `query_api` to reproduce, then `read_file` to find bug

## Implementation Steps

1. Create `plans/task-3.md` (this file)
2. Add `query_api` tool schema to `agent.py`
3. Implement `query_api()` function with authentication
4. Update system prompt with tool selection guidance
5. Add environment variable loading for `LMS_API_KEY` and `AGENT_API_BASE_URL`
6. Run `run_eval.py` and iterate until all 10 questions pass
7. Update `AGENT.md` with lessons learned
8. Create 2 regression tests
9. Test with benchmark questions

## Benchmark Questions

| # | Question | Expected Tool |
|---|----------|---------------|
| 0 | Branch protection steps | `read_file` |
| 1 | SSH connection steps | `read_file` |
| 2 | Python web framework | `read_file` |
| 3 | API router modules | `list_files` |
| 4 | Item count in database | `query_api` |
| 5 | Status code without auth | `query_api` |
| 6 | Completion rate error | `query_api`, `read_file` |
| 7 | Top-learners error | `query_api`, `read_file` |
| 8 | Request lifecycle | `read_file` |
| 9 | ETL idempotency | `read_file` |

## Expected Challenges

1. **API authentication** - need to load `LMS_API_KEY` from correct file
2. **Tool selection** - LLM might call wrong tool for some questions
3. **Error handling** - API errors need to be returned to LLM for diagnosis
4. **Multi-step reasoning** - some questions require multiple tool calls

## Iteration Strategy

1. Run `run_eval.py` to get baseline score
2. For each failing question:
   - Check which tool was called
   - Check if tool arguments were correct
   - Check if answer extraction worked
3. Fix issues one at a time
4. Re-run until all pass
