# AI Code Reviewer Action

GitHub Action customizada que usa a API da OpenAI para revisar pull requests e fornecer sugestões inline.

## Status do Projeto

**Versão:** 1.0.0
**Status:** ✅ Funcional e pronto para uso
**Última atualização:** 10 de Fevereiro de 2026

### Funcionalidades Implementadas

- ✅ Revisão automatizada de código usando OpenAI API (gpt-5.2)
- ✅ Comentários inline em pull requests com blocos de sugestão
- ✅ Suporte a arquivo de regras configurável (`.cursor/rules/RULE.mdc` ou customizado)
- ✅ Notificação inicial automática ao iniciar revisão (configurável)
- ✅ Parsing de diffs com `whatthepatch`
- ✅ Validação de linhas adicionadas para comentários precisos
- ✅ Structured outputs com Pydantic para respostas consistentes
- ✅ Logs informativos e modo debug
- ✅ Gerenciamento de dependências com `uv`
- ✅ Suporte a Python 3.12+

### Tecnologias

- **Python:** 3.12+
- **Gerenciamento de Dependências:** uv
- **APIs:** OpenAI API, GitHub API
- **Bibliotecas principais:**
  - `PyGithub` (2.5.0+) - Interação com GitHub API
  - `openai` (2.18.0) - Cliente OpenAI com structured outputs
  - `whatthepatch` (1.0.6+) - Parsing de diffs
  - `pydantic` (2.10.6+) - Validação e estruturação de dados

## Características

- 🤖 Revisa diffs de pull requests usando modelos GPT da OpenAI
- 💬 Posta comentários inline com sugestões
- 📋 Lê e segue regras específicas do projeto (configurável e opcional)
- ✨ Suporta blocos de sugestão do GitHub para mudanças fáceis de código
- 🎯 Foco em: qualidade de código, melhores práticas, bugs potenciais, performance e segurança
- 🔔 Notificação inicial automática (pode ser desabilitada)
- 🛠️ Sistema de mensagens customizáveis e extensível

## Uso

### Configuração Básica

Adicione este workflow no seu repositório em `.github/workflows/ai-code-review.yaml`:

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

### Configuração com Opções Personalizadas

```yaml
- name: AI Code Review
  uses: cerradoX/ai-code-reviewer@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    openai_code_review_model: 'gpt-5.2'
    system_message: |
      Você é um revisor especialista em segurança.
      Foque especialmente em vulnerabilidades e práticas de segurança.
    debug: 'false'
    post_initial_comment: 'true'  # Opcional: desabilite para não postar comentário inicial
```

## Inputs

| Input | Obrigatório | Padrão | Descrição |
|-------|-------------|--------|-----------|
| `github_token` | Sim | - | Token do GitHub para acesso à API |
| `openai_api_key` | Sim | - | Chave da API OpenAI |
| `openai_code_review_model` | Não | `gpt-5.2` | Modelo para revisão detalhada |
| `system_message` | Não | - | Mensagem de sistema customizada com instruções de revisão |
| `debug` | Não | `false` | Habilita logs de debug |
| `post_initial_comment` | Não | `true` | Posta comentário inicial notificando o início da revisão |
| `rules_file_path` | Não | `.cursor/rules/RULE.mdc` | Caminho relativo para arquivo de regras do projeto (opcional) |

## Configuração de Secrets

### Em Nível de Organização (Recomendado)

Para usar em múltiplos repositórios:

1. Vá em **Organization Settings** → **Secrets and variables** → **Actions**
2. Clique em **New organization secret**
3. Adicione:
   - `OPENAI_API_KEY`: Sua chave da API OpenAI
4. Configure o acesso aos repositórios que devem usar a action

### Em Nível de Repositório

1. Vá em **Settings** → **Secrets and variables** → **Actions**
2. Clique em **New repository secret**
3. Adicione `OPENAI_API_KEY` com sua chave da API OpenAI

> **Nota**: O `GITHUB_TOKEN` é fornecido automaticamente pelo GitHub Actions.

## Regras do Projeto

A action pode carregar regras específicas do projeto para incluir no contexto da revisão. Por padrão, procura por `.cursor/rules/RULE.mdc` no repositório, mas o caminho é **configurável e opcional**.

### Configurar Caminho Customizado

```yaml
- name: AI Code Review
  uses: cerradoX/ai-code-reviewer@v1.0.0
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    rules_file_path: "docs/code-review-rules.md"  # Caminho customizado
```

### Desabilitar Carregamento de Regras

Para não carregar nenhum arquivo de regras:

```yaml
- name: AI Code Review
  uses: cerradoX/ai-code-reviewer@v1.0.0
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    rules_file_path: ""  # Vazio = não carregar regras
```

### Exemplo de Arquivo de Regras

```markdown
# Regras do Projeto

## Estilo de Código
- Use TypeScript estrito
- Preferir const sobre let
- Usar arrow functions para callbacks

## Arquitetura
- Separar lógica de negócio em services
- Controllers apenas para roteamento
- Usar DTOs para validação de entrada
```

> **Nota**: Se o arquivo não existir, a action continua normalmente sem ele. O arquivo é sempre opcional.

## Desenvolvimento

### Setup Local

```bash
# Clone o repositório
git clone git@github.com:cerradoX/ai-code-reviewer.git
cd ai-code-reviewer

# Instale uv se ainda não tiver
curl -LsSf https://astral.sh/uv/install.sh | sh

# Crie o ambiente virtual e instale dependências
uv sync
```

### Estrutura do Projeto

```
ai-code-reviewer/
├── main.py                 # Script principal da action
├── action.yml              # Definição da GitHub Action
├── pyproject.toml          # Configuração do projeto e dependências
├── uv.lock                 # Lock file de dependências
├── .github/
│   └── workflows/
│       └── example.yaml    # Exemplo de workflow
├── LICENSE
└── README.md
```

### Atualizar Dependências

```bash
# Adicionar nova dependência
uv add nome-do-pacote

# Atualizar dependências
uv lock --upgrade

# Remover dependência
uv remove nome-do-pacote
```

### Testar Localmente

Você pode testar a action localmente configurando variáveis de ambiente:

```bash
export INPUT_GITHUB_TOKEN="seu_token"
export INPUT_OPENAI_API_KEY="sua_chave"
export INPUT_OPENAI_CODE_REVIEW_MODEL="gpt-5.2"
export INPUT_DEBUG="true"
export GITHUB_EVENT_PATH="caminho/para/event.json"
export GITHUB_WORKSPACE="caminho/para/workspace"

uv run python main.py
```

## Versionamento

Para usar uma versão específica da action:

```yaml
uses: cerradoX/ai-code-reviewer@v1.0.0  # Tag específica
uses: cerradoX/ai-code-reviewer@main    # Branch main (mais recente)
uses: cerradoX/ai-code-reviewer@abc123  # Commit específico
```

## Exemplo de Workflow Completo

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

      - name: Avisar início da revisão
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --body "🤖 **IA Agent:** Iniciando a revisão do seu código... Aguarde as sugestões."
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: AI Code Review
        uses: cerradoX/ai-code-reviewer@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          openai_code_review_model: "gpt-5.2"
          debug: "false"
```

## Troubleshooting

### A action não está postando comentários

- Verifique se as permissões `pull-requests: write` estão configuradas
- Confirme que o `OPENAI_API_KEY` está configurado corretamente
- Habilite `debug: 'true'` para ver logs detalhados

### Comentários aparecem em linhas erradas

- A action só comenta em linhas que foram **adicionadas** (marcadas com `+` no diff)
- Certifique-se de que o modelo está retornando números de linha válidos

### Rate limits da OpenAI

- Considere adicionar delays entre chamadas para PRs muito grandes
- Use um modelo mais rápido se necessário (ex: `gpt-3.5-turbo`)

## Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

MIT

## Suporte

Para problemas ou dúvidas, abra uma issue no repositório.
