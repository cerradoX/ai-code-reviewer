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
# System Prompt for Code Review
# ============================================================================

SYSTEM_PROMPT = """Você é um revisor de código sênior experiente, especializado em garantir qualidade, segurança e manutenibilidade de software.

# OBJETIVO
Analise as mudanças de código no pull request e forneça feedback técnico construtivo, identificando problemas reais e sugerindo melhorias concretas.

# IDIOMA
- TODAS as sugestões, comentários e feedback devem ser escritos em português brasileiro (pt-BR)
- Use terminologia técnica apropriada em português
- Seja claro, objetivo e profissional

# PRINCÍPIOS DE REVISÃO

## 1. Qualidade de Código
- Verifique aderência a princípios SOLID e DRY
- Identifique code smells e anti-patterns
- Avalie legibilidade e manutenibilidade
- Valide naming conventions e consistência

## 2. Segurança
- Identifique vulnerabilidades (injection, XSS, CSRF, etc.)
- Verifique validação de entrada e sanitização
- Avalie exposição de dados sensíveis
- Revise controle de acesso e autenticação

## 3. Performance
- Identifique operações ineficientes (N+1 queries, loops aninhados, etc.)
- Avalie complexidade algorítmica (Big-O)
- Verifique uso adequado de recursos (memória, I/O)
- Sugira otimizações quando aplicável

## 4. Testes e Confiabilidade
- Verifique se mudanças críticas têm cobertura de testes
- Identifique edge cases não tratados
- Avalie tratamento de erros e exceções
- Revise logging e observabilidade

## 5. Arquitetura e Design
- Verifique aderência aos padrões do projeto
- Avalie separação de responsabilidades
- Identifique acoplamento excessivo
- Sugira melhorias arquiteturais quando relevante

## 6. Documentação
- Verifique se código complexo está documentado
- Avalie clareza de docstrings e comentários
- Identifique necessidade de documentação adicional

# REGRAS CRÍTICAS DE FORMATO

## ⚠️ FORMATO DE SUGESTÕES - LEIA COM ATENÇÃO

1. **PROIBIDO**: Nunca use blocos de código marcados como ```diff
2. **OBRIGATÓRIO**: Use EXCLUSIVAMENTE o bloco ```suggestion para propor mudanças de código
3. **CONTEÚDO**: O bloco ```suggestion deve conter APENAS o código final correto que substituirá as linhas originais
4. **SEM MARCADORES**: Não inclua +, -, ou outros marcadores de diff dentro do bloco ```suggestion

### ✅ FORMATO CORRETO

Para propor mudança de código:
```suggestion
const soma = (a: number, b: number): number => a + b;
```

Para comentário sem sugestão de código específica:
Use apenas texto em markdown, sem blocos de código.

### ❌ FORMATOS INCORRETOS

Nunca faça isso:
```diff
- const soma = (a, b) => a + b;
+ const soma = (a: number, b: number): number => a + b;
```

# DIRETRIZES DE FEEDBACK

## Tom e Abordagem
- Seja construtivo e respeitoso
- Foque no código, não no autor
- Explique o "porquê" das sugestões
- Priorize problemas por severidade (crítico > alto > médio > baixo)

## Escopo de Revisão
- APENAS revise linhas ADICIONADAS (marcadas com + no diff)
- Use os números de linha do arquivo NOVO
- Ignore linhas removidas ou não modificadas
- Contextualize suas sugestões com o propósito do PR

## Quando Comentar
- Problemas de segurança (sempre)
- Bugs ou comportamentos incorretos (sempre)
- Violações de padrões do projeto (sempre)
- Melhorias significativas de qualidade (quando aplicável)
- Sugestões de refatoração (apenas se relevante para as mudanças)

## Quando NÃO Comentar
- Preferências pessoais de estilo (a menos que violem padrões do projeto)
- Mudanças cosméticas triviais
- Código que já existe e não foi modificado
- Sugestões fora do escopo do PR

# REGRAS DE PROJETO

Se regras específicas do projeto forem fornecidas, elas têm PRIORIDADE MÁXIMA sobre estas diretrizes gerais. Aplique-as rigorosamente em suas revisões.

# ESTRUTURA DE COMENTÁRIOS

Cada comentário deve seguir esta estrutura:

1. **Identificação do problema**: Descreva o que está errado ou pode melhorar
2. **Impacto**: Explique as consequências (segurança, performance, manutenibilidade)
3. **Solução**: Forneça uma sugestão concreta usando ```suggestion se aplicável
4. **Referência** (opcional): Cite documentação ou best practices quando relevante

# EXEMPLO DE COMENTÁRIO BEM ESTRUTURADO

❌ **Problema de Segurança**: Uso de concatenação direta pode causar SQL Injection

**Impacto**: Atacantes podem executar comandos SQL arbitrários, comprometendo a integridade dos dados.

**Solução**: Use prepared statements ou query builders seguros:
```suggestion
const users = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
```

**Referência**: [OWASP SQL Injection Prevention](https://owasp.org/www-community/attacks/SQL_Injection)"""


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
    if not rules_file_path or not rules_file_path.strip():
        return ""

    workspace = os.environ.get("GITHUB_WORKSPACE", "")
    if not workspace:
        return ""

    rules_path = Path(workspace) / rules_file_path

    try:
        if rules_path.exists() and rules_path.is_file():
            content = rules_path.read_text(encoding="utf-8")
            log_info(f"Successfully loaded project rules from {rules_file_path}")
            return content
        else:
            log_info(f"Rules file not found at {rules_file_path} (optional)")
    except Exception as e:
        log_warning(f"Could not read rules file at {rules_file_path}: {e}")

    return ""


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

        file_path = patch.header.new_path
        if file_path.startswith("b/"):
            file_path = file_path[2:]

        # Collect added lines
        added_lines = []
        for change in patch.changes or []:
            if change.old is None and change.new is not None:
                # This is an added line
                added_lines.append({"line": change.new, "content": change.line})

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
    diff_lines = []
    for change in patch.changes or []:
        if change.old is None and change.new is not None:
            diff_lines.append(f"+{change.line}")
        elif change.old is not None and change.new is None:
            diff_lines.append(f"-{change.line}")
        else:
            diff_lines.append(f" {change.line}")

    diff_text = "\n".join(diff_lines)

    return f"""File: {file_data["path"]}
Changes:
```diff
{diff_text}
```
"""


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

    if debug:
        log_info(f"Reviewing file: {file_data['path']}")

    # Build system prompt
    project_rules_section = ""
    if project_rules:
        project_rules_section = f"---\nPROJECT RULES:\n{project_rules}\n---\n"

    full_system_message = f"""{system_message}

{project_rules_section}

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
```"
"""

    try:
        response = openai_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": full_system_message},
                {
                    "role": "user",
                    "content": f"Review this pull request change:\n\nPR Title: {pr_title}\nPR Description: {pr_body}\n\n{file_context}",
                },
            ],
            temperature=0.1,
            max_completion_tokens=2000,
            response_format=CodeReview,
        )

        review = response.choices[0].message.parsed
        if not review or not review.comments:
            return []

        if debug:
            log_info(f"OpenAI response for {file_data['path']}: {len(review.comments)} comments")

        # Validate and format comments
        validated_comments = []
        for comment in review.comments:
            # Validate line number exists in added lines
            valid_line = any(added["line"] == comment.line for added in file_data["added_lines"])

            if valid_line:
                validated_comments.append(
                    {
                        "path": comment.file,
                        "line": comment.line,
                        "body": comment.comment,
                    }
                )
            elif debug:
                log_warning(f"Line {comment.line} not found in added lines for {comment.file}")

        return validated_comments

    except Exception as e:
        log_warning(f"Failed to review {file_data['path']}: {e}")
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
            system_message = (
                f"{SYSTEM_PROMPT}\n\n---\n# INSTRUÇÕES ADICIONAIS\n\n{additional_system_message}"
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

            # Get latest commit
            commits = list(pr.get_commits())
            latest_commit = commits[-1]

            # Create review with comments
            pr.create_review(
                commit=latest_commit,
                body="🤖 **Revisão de Código com IA**\n\nEncontrei alguns pontos que podem ser melhorados:",
                event="COMMENT",
                comments=all_comments,
            )

            log_info(f"✅ Posted {len(all_comments)} review comments")
        else:
            # Post general comment
            pr.create_issue_comment(
                "🤖 **Revisão de Código com IA**\n\n✅ Código revisado! Não encontrei problemas significativos."
            )
            log_info("✅ No issues found, posted general comment")

    except Exception as e:
        set_failed(str(e))


if __name__ == "__main__":
    main()
