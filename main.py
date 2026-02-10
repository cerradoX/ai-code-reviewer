#!/usr/bin/env python3
"""AI Code Reviewer GitHub Action.

This action reviews pull requests using OpenAI API and posts inline suggestions.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
import whatthepatch
from github import Auth, Github
from openai import OpenAI
from pydantic import BaseModel, Field

# ============================================================================
# Constants
# ============================================================================

SYSTEM_PROMPT = """You are an experienced senior code reviewer, specialized in ensuring software quality, security, and maintainability.

# OBJECTIVE
Analyze code changes in the pull request and provide constructive technical feedback, identifying real issues and suggesting concrete improvements.

# LANGUAGE
- ALL suggestions, comments, and feedback must be written in US English (en-US)
- Use appropriate technical terminology
- Be clear, objective, and professional

# REVIEW PRINCIPLES

## 1. Code Quality
- Check adherence to SOLID and DRY principles
- Identify code smells and anti-patterns
- Evaluate readability and maintainability
- Validate naming conventions and consistency

## 2. Security
- Identify vulnerabilities (injection, XSS, CSRF, etc.)
- Verify input validation and sanitization
- Evaluate exposure of sensitive data
- Review access control and authentication

## 3. Performance
- Identify inefficient operations (N+1 queries, nested loops, etc.)
- Evaluate algorithmic complexity (Big-O)
- Check appropriate resource usage (memory, I/O)
- Suggest optimizations when applicable

## 4. Testing and Reliability
- Verify critical changes have test coverage
- Identify untreated edge cases
- Evaluate error and exception handling
- Review logging and observability

## 5. Architecture and Design
- Verify adherence to project patterns
- Evaluate separation of concerns
- Identify excessive coupling
- Suggest architectural improvements when relevant

## 6. Documentation
- Verify complex code is documented
- Evaluate clarity of docstrings and comments
- Identify need for additional documentation

# CRITICAL FORMAT RULES

## ⚠️ SUGGESTION FORMAT - READ CAREFULLY

1. **FORBIDDEN**: Never use code blocks marked as ```diff
2. **REQUIRED**: Use EXCLUSIVELY the ```suggestion block to propose code changes
3. **CONTENT**: The ```suggestion block must contain ONLY the final correct code that will replace the original lines
4. **NO MARKERS**: Do not include +, -, or other diff markers inside the ```suggestion block

### ✅ CORRECT FORMAT

To propose a code change:
```suggestion
const sum = (a: number, b: number): number => a + b;
```

For comments without specific code suggestions:
Use only markdown text, without code blocks.

### ❌ INCORRECT FORMATS

Never do this:
```diff
- const sum = (a, b) => a + b;
+ const sum = (a: number, b: number): number => a + b;
```

# FEEDBACK GUIDELINES

## Tone and Approach
- Be constructive and respectful
- Focus on the code, not the author
- Explain the "why" behind suggestions
- Prioritize issues by severity (critical > high > medium > low)

## Review Scope
- ONLY review ADDED lines (marked with + in the diff)
- Use line numbers from the NEW file
- Ignore removed or unmodified lines
- Contextualize your suggestions with the PR purpose

## When to Comment
- Security issues (always)
- Bugs or incorrect behavior (always)
- Violations of project standards (always)
- Significant quality improvements (when applicable)
- Refactoring suggestions (only if relevant to the changes)

## When NOT to Comment
- Personal style preferences (unless they violate project standards)
- Trivial cosmetic changes
- Code that already exists and wasn't modified
- Suggestions outside the PR scope

# PROJECT RULES

If specific project rules are provided, they have MAXIMUM PRIORITY over these general guidelines. Apply them rigorously in your reviews.

# COMMENT STRUCTURE

Each comment should follow this structure:

1. **Issue identification**: Describe what's wrong or can be improved
2. **Impact**: Explain the consequences (security, performance, maintainability)
3. **Solution**: Provide a concrete suggestion using ```suggestion if applicable
4. **Reference** (optional): Cite documentation or best practices when relevant

# WELL-STRUCTURED COMMENT EXAMPLE

❌ **Security Issue**: Direct concatenation can cause SQL Injection

**Impact**: Attackers can execute arbitrary SQL commands, compromising data integrity.

**Solution**: Use prepared statements or safe query builders:
```suggestion
const users = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
```

**Reference**: [OWASP SQL Injection Prevention](https://owasp.org/www-community/attacks/SQL_Injection)"""

# Review messages
REVIEW_HEADER = "🤖 **AI Code Review**"
REVIEW_BODY_WITH_COMMENTS = f"{REVIEW_HEADER}\n\nI found some areas that could be improved:"
REVIEW_BODY_NO_ISSUES = (
    f"{REVIEW_HEADER}\n\n✅ Code reviewed! No significant issues found."
)


class ReviewComment(BaseModel):
    """A single code review comment."""

    file: str = Field(description="Path to the file being reviewed")
    line: int = Field(description="Line number in the new file where the comment applies")
    comment: str = Field(
        description="The review comment or suggestion. Use markdown with ```suggestion blocks for code suggestions."
    )


class CodeReview(BaseModel):
    """Collection of code review comments."""

    comments: list[ReviewComment] = Field(
        default_factory=list, description="List of review comments for the file"
    )


def get_input(name: str, required: bool = False, default: str = "") -> str:
    """Get input value from environment variables.

    Args:
        name(str): Input name
        required(bool): Whether the input is required. Defaults to False.
        default(str): Default value if input not found. Defaults to "".

    Returns:
        str: Input value

    Raises:
        ValueError: If required input is not found
    """
    env_name = f"INPUT_{name.upper()}"
    value = os.environ.get(env_name, default)

    if required and not value:
        raise ValueError(f"Input '{name}' is required but not provided")

    return value


def log_info(message: str) -> None:
    """Log info message."""
    print(f"::notice::{message}")


def log_warning(message: str) -> None:
    """Log warning message."""
    print(f"::warning::{message}")


def log_error(message: str) -> None:
    """Log error message."""
    print(f"::error::{message}")


def set_failed(message: str) -> None:
    """Set action as failed."""
    log_error(message)
    sys.exit(1)


def read_project_rules(rules_file_path: str = "") -> str:
    """Read project rules from a configurable file path.

    Args:
        rules_file_path(str): Relative path to rules file from workspace root.
                              If empty, no rules are loaded. Defaults to "".

    Returns:
        str: Project rules content or empty string if not found
    """
    if not rules_file_path.strip():
        return ""

    workspace = os.environ.get("GITHUB_WORKSPACE", "")
    if not workspace:
        return ""

    rules_path = Path(workspace) / rules_file_path

    try:
        if not rules_path.is_file():
            log_info(f"Rules file not found at {rules_file_path} (optional)")
            return ""

        content = rules_path.read_text(encoding="utf-8")
        log_info(f"Successfully loaded project rules from {rules_file_path}")
        return content
    except Exception as e:
        log_warning(f"Could not read rules file at {rules_file_path}: {e}")
        return ""


def _classify_change(change: Any) -> str:
    """Classify a diff change line.

    Args:
        change: Change object from patch

    Returns:
        str: Line prefix ('+', '-', or ' ')
    """
    if change.old is None and change.new is not None:
        return "+"
    elif change.old is not None and change.new is None:
        return "-"
    return " "


def parse_diff_text(diff_text: str) -> list[dict[str, Any]]:
    """Parse diff text into structured format.

    Args:
        diff_text(str): Unified diff text

    Returns:
        list[dict[str, Any]]: List of file changes with structure
    """
    patches = whatthepatch.parse_patch(diff_text)
    files = []

    for patch in patches:
        if not patch.header or not patch.header.new_path:
            continue

        # Skip deleted files
        if patch.header.new_path == "/dev/null":
            continue

        file_path = patch.header.new_path.removeprefix("b/")

        # Collect added lines
        added_lines = [
            {"line": change.new, "content": change.line}
            for change in (patch.changes or [])
            if change.old is None and change.new is not None
        ]

        if added_lines:
            files.append({"path": file_path, "patch": patch, "added_lines": added_lines})

    return files


def create_file_diff_context(file_data: dict[str, Any]) -> str:
    """Create readable diff context for a file.

    Args:
        file_data(dict[str, Any]): File data with patch information

    Returns:
        str: Formatted diff context
    """
    patch = file_data["patch"]

    # Build unified diff representation
    diff_lines = [
        f"{_classify_change(change)}{change.line}" for change in (patch.changes or [])
    ]

    diff_text = "\n".join(diff_lines)

    return f"""File: {file_data["path"]}
Changes:
```diff
{diff_text}
```
"""


def _build_full_system_message(system_message: str, project_rules: str) -> str:
    """Build the complete system message with project rules if available.

    Args:
        system_message(str): Base system message
        project_rules(str): Project-specific rules

    Returns:
        str: Complete system message
    """
    parts = [system_message]

    if project_rules:
        parts.append(f"---\nPROJECT RULES:\n{project_rules}\n---")

    parts.append(
        """
INSTRUCTIONS:
- Review the code changes and provide constructive feedback
- Only suggest changes for lines that were ADDED (marked with + in the diff)
- Line numbers must match the new file line numbers
- If you want to provide a code suggestion, use markdown with ```suggestion blocks
- Focus on: code quality, best practices, potential bugs, performance, security

Example comment with suggestion:
"Consider using const instead of let here:
```suggestion
const result = calculate();
```\""""
    )

    return "\n\n".join(parts)


def _validate_comment_line(
    comment_line: int, added_lines: list[dict[str, Any]]
) -> bool:
    """Validate that a comment line exists in the added lines.

    Args:
        comment_line(int): Line number from comment
        added_lines(list[dict[str, Any]]): List of added lines

    Returns:
        bool: True if line is valid
    """
    return any(added["line"] == comment_line for added in added_lines)


def review_file_with_openai(
    openai_client: OpenAI,
    model: str,
    system_message: str,
    project_rules: str,
    pr_title: str,
    pr_body: str,
    file_data: dict[str, Any],
    debug: bool,
) -> list[dict[str, Any]]:
    """Review a file using OpenAI API with structured outputs.

    Args:
        openai_client(OpenAI): OpenAI client instance
        model(str): Model name to use
        system_message(str): System message with instructions
        project_rules(str): Project-specific rules
        pr_title(str): Pull request title
        pr_body(str): Pull request body
        file_data(dict[str, Any]): File data to review
        debug(bool): Enable debug logging

    Returns:
        list[dict[str, Any]]: List of review comments
    """
    file_context = create_file_diff_context(file_data)
    file_path = file_data["path"]

    if debug:
        log_info(f"Reviewing file: {file_path}")

    full_system_message = _build_full_system_message(system_message, project_rules)

    # Build user message
    user_message = "\n\n".join(
        [
            "Review this pull request change:",
            f"PR Title: {pr_title}",
            f"PR Description: {pr_body}",
            file_context,
        ]
    )

    try:
        response = openai_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": full_system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_completion_tokens=2000,
            response_format=CodeReview,
        )

        review = response.choices[0].message.parsed
        if not review or not review.comments:
            return []

        if debug:
            log_info(f"OpenAI response for {file_path}: {len(review.comments)} comments")

        # Validate and format comments
        validated_comments = []
        for comment in review.comments:
            if _validate_comment_line(comment.line, file_data["added_lines"]):
                validated_comments.append(
                    {"path": comment.file, "line": comment.line, "body": comment.comment}
                )
            elif debug:
                log_warning(
                    f"Line {comment.line} not found in added lines for {comment.file}"
                )

        return validated_comments

    except Exception as e:
        log_warning(f"Failed to review {file_path}: {e}")
        return []


def main() -> None:
    """Main entry point for the action."""
    try:
        # Get inputs
        github_token = get_input("github_token", required=True)
        openai_api_key = get_input("openai_api_key", required=True)
        code_review_model = get_input("openai_code_review_model", default="gpt-5.2")
        additional_system_message = get_input("system_message", default="")
        rules_file_path = get_input("rules_file_path", default=".cursor/rules/RULE.mdc")
        debug = get_input("debug", default="false").lower() == "true"

        # Build system message using constant with optional additional instructions
        system_message = SYSTEM_PROMPT
        if additional_system_message.strip():
            system_message = "\n\n".join(
                [SYSTEM_PROMPT, "---", "# ADDITIONAL INSTRUCTIONS", additional_system_message]
            )

        # Get GitHub context
        github_event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not github_event_path:
            set_failed("GITHUB_EVENT_PATH not found")
            return

        with open(github_event_path, encoding="utf-8") as f:
            event = json.load(f)

        if "pull_request" not in event:
            set_failed("This action can only be run on pull_request events")
            return

        pr_number = event["pull_request"]["number"]
        pr_title = event["pull_request"]["title"]
        pr_body = event["pull_request"].get("body", "")
        repo_full_name = event["repository"]["full_name"]

        if debug:
            log_info(f"Reviewing PR #{pr_number}: {pr_title}")

        # Initialize clients
        auth = Auth.Token(github_token)
        github_client = Github(auth=auth)

        openai_client = OpenAI(api_key=openai_api_key, max_retries=2, timeout=60.0)

        # Get repository and PR
        repo = github_client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        # Get PR diff
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3.diff",
        }
        diff_response = requests.get(pr.url, headers=headers)
        diff_text = diff_response.text

        if not diff_text or not diff_text.strip():
            log_info("No changes to review")
            return

        # Parse diff
        files = parse_diff_text(diff_text)
        if debug:
            log_info(f"Found {len(files)} changed files")

        if not files:
            log_info("No files to review")
            return

        # Read project rules
        project_rules = read_project_rules(rules_file_path)

        # Review each file
        all_comments = []
        for file_data in files:
            comments = review_file_with_openai(
                openai_client,
                code_review_model,
                system_message,
                project_rules,
                pr_title,
                pr_body,
                file_data,
                debug,
            )
            all_comments.extend(comments)

        # Post review comments
        if all_comments:
            if debug:
                log_info(f"Posting {len(all_comments)} review comments")

            # Get latest commit efficiently using reversed iteration
            latest_commit = next(iter(pr.get_commits().reversed))

            # Create review with comments
            pr.create_review(
                commit=latest_commit,
                body=REVIEW_BODY_WITH_COMMENTS,
                event="COMMENT",
                comments=all_comments,
            )

            log_info(f"✅ Posted {len(all_comments)} review comments")
        else:
            # Post general comment
            pr.create_issue_comment(REVIEW_BODY_NO_ISSUES)
            log_info("✅ No issues found, posted general comment")

    except Exception as e:
        set_failed(str(e))


if __name__ == "__main__":
    main()
