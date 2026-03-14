#!/usr/bin/env python3
"""
Agent CLI - System Agent with query_api tool.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON line to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Maximum number of tool calls per question
MAX_ITERATIONS = 10

# Project root for file access restrictions
PROJECT_ROOT = Path(__file__).parent.resolve()


def load_env():
    """Load environment variables from .env.agent.secret and .env.docker.secret."""
    # Load LLM config from .env.agent.secret
    agent_env_file = PROJECT_ROOT / ".env.agent.secret"
    if agent_env_file.exists():
        load_dotenv(agent_env_file)
    
    # Load LMS API key from .env.docker.secret
    docker_env_file = PROJECT_ROOT / ".env.docker.secret"
    if docker_env_file.exists():
        # Load into a separate namespace to avoid conflicts
        load_dotenv(docker_env_file, override=True)


def get_tool_schemas():
    """Return tool schemas for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to read file contents like source code, documentation, or configuration files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root, e.g., 'wiki/git-workflow.md' or 'backend/app/routers/items.py'"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root, e.g., 'wiki' or 'backend/app/routers'"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the backend LMS API. Use this for data-dependent questions like item counts, analytics, status codes, or to reproduce API errors. Use authenticate=false to test unauthenticated access.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, etc."
                        },
                        "path": {
                            "type": "string",
                            "description": "API path, e.g., '/items/', '/analytics/completion-rate', '/pipeline/sync'"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT requests"
                        },
                        "authenticate": {
                            "type": "boolean",
                            "description": "Whether to include authentication header. Default true. Set false to test unauthenticated access."
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def validate_path(path: str) -> tuple:
    """
    Validate that a path is safe and within the project directory.
    
    Returns:
        (is_valid, error_message)
    """
    if not path:
        return False, "Empty path"
    
    # Reject absolute paths
    if path.startswith("/"):
        return False, "Absolute paths not allowed"
    
    # Reject path traversal
    if ".." in path:
        return False, "Path traversal not allowed"
    
    # Resolve the full path
    full_path = (PROJECT_ROOT / path).resolve()
    
    # Ensure it's within project root
    try:
        full_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return False, "Path outside project directory"
    
    return True, ""


def read_file(path: str) -> str:
    """
    Read a file from the project repository.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return f"Error: {error}"
    
    file_path = PROJECT_ROOT / path
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        content = file_path.read_text()
        # Truncate very long files
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (truncated)"
        return content
    except Exception as e:
        return f"Error: {str(e)}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return f"Error: {error}"
    
    dir_path = PROJECT_ROOT / path
    
    if not dir_path.exists():
        return f"Error: Path not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = sorted([e.name for e in dir_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"


def query_api(method: str, path: str, body: str = None, authenticate: bool = True) -> str:
    """
    Query the backend LMS API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path
        body: Optional JSON request body
        authenticate: Whether to include auth header (default True)
        
    Returns:
        JSON response with status_code and body, or error message
    """
    api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.getenv("LMS_API_KEY")
    
    url = f"{api_base}{path}"
    headers = {}
    
    if authenticate:
        if not lms_api_key:
            return "Error: LMS_API_KEY not configured. Set it in .env.docker.secret"
        headers["Authorization"] = f"Bearer {lms_api_key}"
    
    if method in ["POST", "PUT"]:
        headers["Content-Type"] = "application/json"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            data = json.loads(body) if body else {}
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return f"Error: Unsupported method: {method}"
        
        result = {
            "status_code": response.status_code,
            "body": response.text[:5000]  # Truncate long responses
        }
        return json.dumps(result)
    
    except requests.exceptions.Timeout:
        return "Error: API request timed out (30s)"
    except requests.exceptions.RequestException as e:
        return f"Error: API request failed: {str(e)}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON body: {str(e)}"


def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool and return the result.
    """
    if tool_name == "read_file":
        path = args.get("path", "")
        return read_file(path)
    
    elif tool_name == "list_files":
        path = args.get("path", "")
        return list_files(path)
    
    elif tool_name == "query_api":
        method = args.get("method", "GET")
        path = args.get("path", "")
        body = args.get("body")
        authenticate = args.get("authenticate", True)
        return query_api(method, path, body, authenticate)
    
    else:
        return f"Error: Unknown tool: {tool_name}"


def call_llm(messages: list, tools: list) -> dict:
    """
    Call the LLM API and return the response.
    """
    api_base = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not all([api_base, api_key, model]):
        print("Error: Missing LLM configuration in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Error: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: LLM request failed: {e}", file=sys.stderr)
        sys.exit(1)


def extract_source_from_answer(answer: str, tool_calls: list) -> str:
    """
    Extract source reference from the answer or tool calls.
    """
    # Look for patterns like wiki/something.md or path/to/file.md
    pattern = r'(\w+/[\w-]+\.md)'
    matches = re.findall(pattern, answer)
    
    if matches:
        return matches[0]
    
    # Fall back to the last read_file path
    for call in reversed(tool_calls):
        if call.get("tool") == "read_file":
            return call.get("args", {}).get("path", "")
    
    return ""


def run_agentic_loop(question: str) -> dict:
    """
    Run the agentic loop to answer a question.
    """
    # System prompt for the system agent
    system_prompt = """You are a helpful system agent with access to tools:
- list_files(path): List files in a directory
- read_file(path): Read contents of a file (source code, documentation, config)
- query_api(method, path, body?, authenticate?): Query the backend LMS API

Tool selection guide:
- Wiki/documentation questions → use list_files and read_file on wiki/
- Source code questions (framework, implementation) → use read_file directly on likely files (backend/app/main.py, backend/app/routers/*.py, pyproject.toml)
- Data queries (counts, analytics, status codes) → use query_api
- Bug diagnosis → use query_api to reproduce, then read_file to find the bug
- To test unauthenticated access, use query_api with authenticate=false

Always use the exact parameter names: 'path' for file tools, 'method' and 'path' for query_api.
For query_api, common paths: /items/, /analytics/completion-rate, /analytics/top-learners, /pipeline/sync

To check status code without auth, use: query_api(method="GET", path="/items/", authenticate=false)

For Python web framework questions, read: backend/app/main.py or pyproject.toml"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tools = get_tool_schemas()
    tool_calls_log = []
    
    for iteration in range(MAX_ITERATIONS):
        print(f"\n[Iteration {iteration + 1}/{MAX_ITERATIONS}]", file=sys.stderr)
        
        data = call_llm(messages, tools)
        
        choice = data["choices"][0]["message"]
        
        # Check for tool calls
        tool_calls = choice.get("tool_calls", [])
        
        if tool_calls:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": choice.get("content"),
                "tool_calls": tool_calls
            })
            
            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                
                print(f"  Executing {tool_name}({args})", file=sys.stderr)
                
                result = execute_tool(tool_name, args)
                
                # Log the tool call
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result
                })
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": result
                })
            
            # Continue the loop
            continue
        
        # No tool calls - we have the final answer
        answer = choice.get("content", "")
        source = extract_source_from_answer(answer, tool_calls_log)
        
        return {
            "answer": answer,
            "source": source,
            "tool_calls": tool_calls_log
        }
    
    # Max iterations reached
    return {
        "answer": "Maximum tool calls reached. Partial answer may be incomplete.",
        "source": "",
        "tool_calls": tool_calls_log
    }


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    load_env()
    result = run_agentic_loop(question)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
