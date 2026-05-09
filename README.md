# Jira Universal MCP (Python)

MCP em Python para conectar no Jira Cloud e manipular qualquer endpoint da API REST (Platform, Agile, etc).

## 1) Credenciais (Jira Cloud)

Para Jira Cloud (seu caso: `tigasparzin.atlassian.net`), use:

- `JIRA_BASE_URL`: URL da instancia
- `JIRA_EMAIL`: e-mail da conta Atlassian
- `JIRA_API_TOKEN`: token de API da Atlassian (nao e senha)

Como gerar o token:

1. Acesse: https://id.atlassian.com/manage-profile/security/api-tokens
2. Clique em **Create API token**.
3. De um nome (ex.: `codex-mcp-jira`) e copie o token gerado.
4. Guarde em local seguro; depois nao e possivel visualizar o token completo novamente.

## 2) Configurar ambiente

1. Copie `.env.example` para `.env`.
2. Preencha os valores reais:

```env
JIRA_BASE_URL=https://tigasparzin.atlassian.net
JIRA_EMAIL=seu-email-atlassian@dominio.com
JIRA_API_TOKEN=seu_token
JIRA_TIMEOUT_SECONDS=30
```

## 3) Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4) Rodar o servidor MCP

```bash
python jira_mcp_server.py
```

Esse servidor usa transporte `stdio`, ideal para ser executado diretamente pelo cliente MCP (incluindo o Codex).

## 5) Conectar no Codex (exemplo de comando)

Configure um servidor MCP no Codex apontando para:

- Command: `python`
- Args: `C:\\Users\\tigasparzin\\Documents\\New project\\jira_mcp_server.py`
- Working directory: `C:\\Users\\tigasparzin\\Documents\\New project`
- Env file: `C:\\Users\\tigasparzin\\Documents\\New project\\.env`

## 6) Ferramentas disponiveis

- `jira_healthcheck`: valida credenciais (`/rest/api/3/myself`)
- `jira_get`
- `jira_post`
- `jira_put`
- `jira_patch`
- `jira_delete`
- `jira_request` (universal)
- `jira_upload_attachment` (anexos de issue)

Com isso voce cobre qualquer recurso da API Jira que sua conta tenha permissao para acessar.

## 7) Exemplos para seu board

Board SCRUM (id `1`):

- Detalhes do board:
  - `path`: `/rest/agile/1.0/board/1`
- Sprints do board:
  - `path`: `/rest/agile/1.0/board/1/sprint`
- Issues do board:
  - `path`: `/rest/agile/1.0/board/1/issue`

Exemplo usando ferramenta universal:

```json
{
  "method": "GET",
  "path": "/rest/agile/1.0/board/1/sprint",
  "query": { "maxResults": 50 }
}
```

Exemplo de upload de anexo:

```json
{
  "issue_key_or_id": "SCRUM-123",
  "file_path": "C:\\\\caminho\\\\arquivo.pdf"
}
```

Se precisar enviar corpo nao-JSON para algum endpoint especifico, use `body_text` + `extra_headers` com `Content-Type` adequado.

## Seguranca

- Nunca commitar `.env`.
- Revogue e regenere o token imediatamente se ele vazar.
- As permissoes da API seguem as permissoes do usuario Jira autenticado.
