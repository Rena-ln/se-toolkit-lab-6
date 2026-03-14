#!/usr/bin/env python3
"""
Regression tests for agent.py

Tests that the agent outputs valid JSON with required fields.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> dict:
    """Run the agent and return the parsed output."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        ["uv", "run", str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise AssertionError(f"Agent failed with exit code {result.returncode}: {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")


def test_agent_basic_question():
    """Test that agent.py returns valid JSON with answer and tool_calls."""
    output = run_agent("What is 2+2? Answer in one word.")

    # Check required fields
    assert "answer" in output, "Missing 'answer' field in output"
    assert "source" in output, "Missing 'source' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    # Check that answer is non-empty
    assert len(output["answer"]) > 0, "Answer is empty"

    print(f"✓ Test passed: answer='{output['answer'][:50]}...', tool_calls={len(output['tool_calls'])}")


def test_agent_list_files():
    """Test that agent uses list_files tool for wiki directory question."""
    output = run_agent("What files are in the wiki directory?")

    # Check that tool_calls is populated
    assert len(output["tool_calls"]) > 0, "Expected tool_calls to be populated"

    # Check that list_files was used
    tools_used = [call["tool"] for call in output["tool_calls"]]
    assert "list_files" in tools_used, f"Expected list_files in tool_calls, got: {tools_used}"

    # Check that the result contains wiki files
    list_files_call = next((c for c in output["tool_calls"] if c["tool"] == "list_files"), None)
    assert list_files_call is not None, "list_files call not found"
    assert "git.md" in list_files_call["result"], "Expected git.md in list_files result"

    print(f"✓ Test passed: list_files used, found {len(output['tool_calls'])} tool calls")


def test_agent_read_file():
    """Test that agent uses read_file tool for merge conflict question."""
    output = run_agent("How do you resolve a merge conflict in Git?")

    # Check that tool_calls is populated
    assert len(output["tool_calls"]) > 0, "Expected tool_calls to be populated"

    # Check that read_file was used
    tools_used = [call["tool"] for call in output["tool_calls"]]
    assert "read_file" in tools_used, f"Expected read_file in tool_calls, got: {tools_used}"

    # Check that the source references a wiki file
    assert "wiki/" in output["source"] or ".md" in output["source"], \
        f"Expected wiki source, got: {output['source']}"

    # Check that the answer mentions conflict resolution
    answer_lower = output["answer"].lower()
    assert any(word in answer_lower for word in ["conflict", "merge", "git"]), \
        "Expected answer to mention merge conflict resolution"

    print(f"✓ Test passed: read_file used, source={output['source']}")


def test_agent_query_api():
    """Test that agent uses query_api tool for database question."""
    output = run_agent("How many items are in the database? Query the API.")

    # Check that tool_calls is populated
    assert len(output["tool_calls"]) > 0, "Expected tool_calls to be populated"

    # Check that query_api was used
    tools_used = [call["tool"] for call in output["tool_calls"]]
    assert "query_api" in tools_used, f"Expected query_api in tool_calls, got: {tools_used}"

    # Check that the answer contains a number
    answer_lower = output["answer"].lower()
    assert any(char.isdigit() for char in output["answer"]), \
        "Expected answer to contain a number"

    print(f"✓ Test passed: query_api used, answer mentions items")


def test_agent_query_api_unauthenticated():
    """Test that agent can query API without auth to get status code."""
    output = run_agent("What HTTP status code without authentication for /items/? Use authenticate=false.")

    # Check that tool_calls is populated
    assert len(output["tool_calls"]) > 0, "Expected tool_calls to be populated"

    # Check that query_api was used
    tools_used = [call["tool"] for call in output["tool_calls"]]
    assert "query_api" in tools_used, f"Expected query_api in tool_calls, got: {tools_used}"

    # Check that the answer mentions 401 or 403
    answer_lower = output["answer"].lower()
    assert any(code in answer_lower for code in ["401", "403", "unauthorized", "forbidden"]), \
        f"Expected answer to mention 401/403, got: {output['answer']}"

    print(f"✓ Test passed: query_api with authenticate=false, status code found")


if __name__ == "__main__":
    print("Running agent.py regression tests...\n")

    try:
        test_agent_basic_question()
        test_agent_list_files()
        test_agent_read_file()
        test_agent_query_api()
        test_agent_query_api_unauthenticated()
        print("\n✓ All tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}", file=sys.stderr)
        sys.exit(1)
