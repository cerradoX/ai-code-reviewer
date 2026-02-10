# AI Code Reviewer Action

GitHub Action that uses OpenAI to review pull requests and provide inline suggestions with code improvements.

## Features

- 🤖 Automated code review using OpenAI GPT models
- 💬 Inline comments on pull requests with suggestion blocks
- 📋 Optional project-specific rules file support
- 🎯 Focus on code quality, best practices, bugs, performance, and security

## Usage

Add this workflow to `.github/workflows/ai-code-review.yaml`:

```yaml
name: AI Code Review

on:
  pull_request:
    branches: [main]
    types: [opened, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: AI Code Review
        uses: cerradoX/ai-code-reviewer@v1.0.0
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

For a complete example with all options, see [.github/workflows/example.yaml](.github/workflows/example.yaml).

## Configuration

### Required Inputs

| Input            | Description                  |
|------------------|------------------------------|
| `github_token`   | GitHub token (auto-provided) |
| `openai_api_key` | OpenAI API key               |

### Optional Inputs

| Input                      | Default                  | Description                              |
|----------------------------|--------------------------|------------------------------------------|
| `openai_code_review_model` | `gpt-5.2`                | OpenAI model to use                      |
| `system_message`           | -                        | Custom instructions for the reviewer     |
| `debug`                    | `false`                  | Enable debug logs                        |
| `post_initial_comment`     | `true`                   | Post comment when review starts          |
| `rules_file_path`          | `.cursor/rules/RULE.mdc` | Path to project rules file (optional)    |

### Setup OpenAI API Key

**Repository Level:**

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add `OPENAI_API_KEY` with your OpenAI API key

**Organization Level:**

1. Go to **Organization Settings** → **Secrets and variables** → **Actions**
2. Click **New organization secret**
3. Add `OPENAI_API_KEY` and configure repository access

## Development

### Setup

```bash
# Clone repository
git clone git@github.com:cerradoX/ai-code-reviewer.git
cd ai-code-reviewer

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Test Locally

```bash
export INPUT_GITHUB_TOKEN="your_token"
export INPUT_OPENAI_API_KEY="your_key"
export INPUT_DEBUG="true"
export GITHUB_EVENT_PATH="path/to/event.json"
export GITHUB_WORKSPACE="path/to/workspace"

uv run python main.py
```

## License

MIT
