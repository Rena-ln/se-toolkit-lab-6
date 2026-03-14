# Task 2 Plan: The Documentation Agent

## Overview

Task 2 extends the agent from Task 1 with:
1. Two tools: `read_file` and `list_files`
2. An agentic loop that executes tool calls and feeds results back to the LLM
3. A `source` field in the output to reference wiki sections

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
```

## Tool Schemas

### `read_file`

**Description:** Read a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root

**Returns:** File contents as string, or error message

**Security:** Block `../` path traversal

**Schema:**
```json
{
  "name": "read_file",
  "description": "Read a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

### `list_files`

**Description:** List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root

**Returns:** Newline-separated listing of entries

**Security:** Block `../` path traversal

**Schema:**
```json
{
  "name": "list_files",
  "description": "List files and directories at a given path",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative directory path from project root"}
    },
    "required": ["path"]
  }
}
```

## Agentic Loop

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question}
]

for iteration in range(MAX_ITERATIONS):  # max 10 tool calls
    response = call_llm(messages, tools)
    
    if response has tool_calls:
        for tool_call in tool_calls:
            result = execute_tool(tool_call)
            record tool_call with result
        Append tool results to messages
        continue
    else:
        # Final answer
        extract answer and source
        return JSON output
```

## System Prompt

The system prompt should instruct the LLM to:
1. Use `list_files` to discover wiki files
2. Use `read_file` to find the answer
3. Include source reference (file path + section anchor)
4. Stop after finding the answer (max 10 tool calls)

## Output Format

```json
{
  "answer": "...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Implementation Steps

1. Create `plans/task-2.md` (this file)
2. Add tool schemas to `agent.py`
3. Implement `read_file()` and `list_files()` functions
4. Add agentic loop with max 10 iterations
5. Update output JSON to include `source` and `tool_calls`
6. Update `AGENT.md` documentation
7. Create 2 regression tests
8. Test with wiki questions

## Security

- Validate paths: reject `../` or absolute paths
- Only allow paths within project root
- Use `Path.resolve()` to verify final path

## Testing

Test questions:
1. `"How do you resolve a merge conflict?"` → should use `read_file` on `wiki/git-workflow.md`
2. `"What files are in the wiki?"` → should use `list_files` on `wiki/`
