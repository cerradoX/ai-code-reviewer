# AI Code Reviewer Action

Custom GitHub Action that uses OpenAI API to review pull requests and provide inline suggestions.

## Project Status

**Version:** 1.0.0
**Status:** ✅ Functional and ready to use
**Last updated:** February 10, 2026

### Implemented Features

- ✅ Automated code review using OpenAI API (gpt-5.2)
- ✅ Inline comments on pull requests with suggestion blocks
- ✅ Configurable rules file support (`.cursor/rules/RULE.mdc` or custom)
- ✅ Automatic initial notification when starting review (configurable)
- ✅ Diff parsing with `whatthepatch`
- ✅ Added lines validation for accurate comments
- ✅ Structured outputs with Pydantic for consistent responses
- ✅ Informative logs and debug mode
- ✅ Dependency management with `uv`
- ✅ Python 3.12+ support

### Technologies

- **Python:** 3.12+
- **Dependency Management:** uv
- **APIs:** OpenAI API, GitHub API
- **Main Libraries:**
  - `PyGithub` (2.5.0+) - GitHub API interaction
  - `openai` (2.18.0) - OpenAI client with structured outputs
  - `whatthepatch` (1.0.6+) - Diff parsing
  - `pydantic` (2.10.6+) - Data validation and structuring

## Features

- 🤖 Reviews pull request diffs using OpenAI GPT models
- 💬 Posts inline comments with suggestions
- 📋 Reads and follows project-specific rules (configurable and optional)
- ✨ Supports GitHub suggestion blocks for easy code changes
- 🎯 Focus on: code quality, best practices, potential bugs, performance, and security
- 🔔 Automatic initial notification (can be disabled)
- 🛠️ Customizable and extensible messaging system

## Usage

### Basic Configuration

Add this workflow to your repository in `.github/workflows/ai-code-review.yaml`:

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
        uses: cerradoX/ai-code-reviewer@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### Configuration with Custom Options

```yaml
- name: AI Code Review
  uses: cerradoX/ai-code-reviewer@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    openai_code_review_model: 'gpt-5.2'
    system_message: |
      You are a security expert reviewer.
      Focus especially on vulnerabilities and security practices.
    debug: 'false'
    post_initial_comment: 'true'  # Optional: disable to not post initial comment
```

## Inputs

| Input                      | Required | Default                  | Description                                           |
|----------------------------|----------|--------------------------|-------------------------------------------------------|
| `github_token`             | Yes      | -                        | GitHub token for API access                           |
| `openai_api_key`           | Yes      | -                        | OpenAI API key                                        |
| `openai_code_review_model` | No       | `gpt-5.2`                | Model for detailed review                             |
| `system_message`           | No       | -                        | Custom system message with review instructions        |
| `debug`                    | No       | `false`                  | Enable debug logs                                     |
| `post_initial_comment`     | No       | `true`                   | Post initial comment notifying review start           |
| `rules_file_path`          | No       | `.cursor/rules/RULE.mdc` | Relative path to project rules file (optional)        |

## Secrets Configuration

### Organization Level (Recommended)

To use across multiple repositories:

1. Go to **Organization Settings** → **Secrets and variables** → **Actions**
2. Click **New organization secret**
3. Add:
   - `OPENAI_API_KEY`: Your OpenAI API key
4. Configure access to repositories that should use the action

### Repository Level

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add `OPENAI_API_KEY` with your OpenAI API key

> **Note**: The `GITHUB_TOKEN` is automatically provided by GitHub Actions.

## Project Rules

The action can load project-specific rules to include in the review context. By default, it looks for `.cursor/rules/RULE.mdc` in the repository, but the path is **configurable and optional**.

### Configure Custom Path

```yaml
- name: AI Code Review
  uses: cerradoX/ai-code-reviewer@v1.0.0
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    rules_file_path: "docs/code-review-rules.md"  # Custom path
```

### Disable Rules Loading

To not load any rules file:

```yaml
- name: AI Code Review
  uses: cerradoX/ai-code-reviewer@v1.0.0
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    rules_file_path: ""  # Empty = don't load rules
```

### Example Rules File

```markdown
# Project Rules

## Code Style
- Use strict TypeScript
- Prefer const over let
- Use arrow functions for callbacks

## Architecture
- Separate business logic in services
- Controllers only for routing
- Use DTOs for input validation
```

> **Note**: If the file doesn't exist, the action continues normally without it. The file is always optional.

## Development

### Local Setup

```bash
# Clone the repository
git clone git@github.com:cerradoX/ai-code-reviewer.git
cd ai-code-reviewer

# Install uv if you don't have it yet
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### Project Structure

```
ai-code-reviewer/
├── main.py                 # Main action script
├── action.yml              # GitHub Action definition
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Dependencies lock file
├── .github/
│   └── workflows/
│       └── example.yaml    # Workflow example
├── LICENSE
└── README.md
```

### Update Dependencies

```bash
# Add new dependency
uv add package-name

# Update dependencies
uv lock --upgrade

# Remove dependency
uv remove package-name
```

### Test Locally

You can test the action locally by setting environment variables:

```bash
export INPUT_GITHUB_TOKEN="your_token"
export INPUT_OPENAI_API_KEY="your_key"
export INPUT_OPENAI_CODE_REVIEW_MODEL="gpt-5.2"
export INPUT_DEBUG="true"
export GITHUB_EVENT_PATH="path/to/event.json"
export GITHUB_WORKSPACE="path/to/workspace"

uv run python main.py
```

## Versioning

To use a specific version of the action:

```yaml
uses: cerradoX/ai-code-reviewer@v1.0.0  # Specific tag
uses: cerradoX/ai-code-reviewer@main    # Main branch (latest)
uses: cerradoX/ai-code-reviewer@abc123  # Specific commit
```

## Complete Workflow Example

```yaml
name: AI Code Review

on:
  pull_request:
    branches:
      - main
      - develop
    types: [opened, reopened, synchronize]

concurrency:
  group: ${{ github.repository }}-${{ github.event.pull_request.number }}-${{ github.workflow }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: AI Code Review
        uses: cerradoX/ai-code-reviewer@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          openai_code_review_model: "gpt-5.2"
          debug: "false"
```

## Troubleshooting

### Action is not posting comments

- Check if `pull-requests: write` permissions are configured
- Confirm that `OPENAI_API_KEY` is configured correctly
- Enable `debug: 'true'` to see detailed logs

### Comments appear on wrong lines

- The action only comments on lines that were **added** (marked with `+` in the diff)
- Make sure the model is returning valid line numbers

### OpenAI rate limits

- Consider adding delays between calls for very large PRs
- Use a faster model if necessary (e.g., `gpt-3.5-turbo`)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## License

MIT

## Support

For issues or questions, open an issue in the repository.
