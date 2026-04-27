# MCP Server Mode — Design Spec

## Goal

Add MCP (Model Context Protocol) Server mode to agency-orchestrator, enabling AI coding tools like Claude Code and Cursor to directly invoke workflow operations (run, validate, compose, etc.) via the standard MCP stdio protocol.

## Background

Currently, AI tools interact with agency-orchestrator through:
1. Shell commands (`ao run`, `ao compose`, etc.)
2. Integration guide files in `integrations/` (manual setup per tool)

MCP Server mode eliminates manual setup — users add one line to their MCP config and all 6 workflow tools become available natively.

## Architecture

```
AI Tool (Claude Code / Cursor / etc.)
    │
    │ stdin/stdout (MCP JSON-RPC over stdio)
    │
    ▼
ao serve (StdioServerTransport)
    │
    ├── run_workflow      → run() from src/index.ts
    ├── validate_workflow → parseWorkflow() + validateWorkflow()
    ├── list_workflows    → glob workflows/**/*.yaml
    ├── plan_workflow     → parseWorkflow() + buildDAG() + formatDAG()
    ├── compose_workflow  → composeWorkflow() from src/cli/compose.ts
    └── list_roles        → listAgents() from src/agents/loader.ts
```

**Transport:** `StdioServerTransport` from `@modelcontextprotocol/sdk/server/stdio.js`

**Design principle:** Each tool is a thin wrapper around existing functions. No new business logic in the MCP layer.

## Tools

### 1. run_workflow

Execute a YAML workflow with the DAG engine.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path to workflow YAML file |
| `inputs` | object | No | Key-value input variables (e.g. `{"premise": "..."}`) |
| `provider` | string | No | Override LLM provider (deepseek/claude/openai/ollama) |
| `model` | string | No | Override model name |

**Implementation:** Call `run(resolve(path), inputs, { quiet: true, llmOverride })`. Return `result.outputs` (final step content) + token summary.

**Returns:** Final step output text + token usage summary.

**Error handling:** Catch and return structured error message (missing file, validation failure, LLM error, timeout).

### 2. validate_workflow

Validate a workflow YAML without executing.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path to workflow YAML file |

**Implementation:** Call `parseWorkflow(resolve(path))` then `validateWorkflow(workflow)`.

**Returns:** Workflow name, step count, input count, validation errors (if any).

### 3. list_workflows

List available workflow templates.

**Parameters:** None.

**Implementation:** Glob `workflows/**/*.yaml` from the project root. For each file, parse YAML to extract `name` and `description` fields.

**Returns:** Array of `{ file, name, description }`.

### 4. plan_workflow

Show the DAG execution plan.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path to workflow YAML file |

**Implementation:** Call `parseWorkflow()` → `validateWorkflow()` → `buildDAG()` → `formatDAG()`.

**Returns:** Text representation of the DAG (levels, parallelism, dependencies).

### 5. compose_workflow

Generate a workflow YAML from a natural language description using AI.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `description` | string | Yes | One-sentence workflow description |
| `provider` | string | No | LLM provider (default: deepseek) |
| `model` | string | No | Model name |

**Implementation:** Call `composeWorkflow({ description, agentsDir, llmConfig })`.

**Returns:** Generated YAML content + saved file path + validation warnings.

### 6. list_roles

List available AI roles from the agents directory.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agents_dir` | string | No | Path to agents directory (auto-resolved if omitted) |

**Implementation:** Call `listAgents(resolve(agentsDir))`.

**Returns:** Array of roles with name, description, emoji, category.

## CLI Entry Point

New command: `ao serve`

```bash
ao serve              # Start MCP stdio server
ao serve --verbose    # With debug logging to stderr
```

Implementation in `src/cli.ts`: add `case 'serve'` that imports and calls `startServer()` from `src/mcp/server.ts`.

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Create | `src/mcp/server.ts` | MCP server: tool definitions + handlers (~250 lines) |
| Modify | `src/cli.ts` | Add `ao serve` command |
| Modify | `package.json` | Add `@modelcontextprotocol/sdk` dependency |

## User Configuration

### Claude Code (settings.json)

```json
{
  "mcpServers": {
    "agency-orchestrator": {
      "command": "npx",
      "args": ["agency-orchestrator", "serve"]
    }
  }
}
```

### Cursor (.cursor/mcp.json)

```json
{
  "mcpServers": {
    "agency-orchestrator": {
      "command": "npx",
      "args": ["agency-orchestrator", "serve"]
    }
  }
}
```

## Error Handling

All tools follow the same pattern:
1. Validate parameters (required fields present, path exists)
2. Call underlying function in try/catch
3. Return `isError: true` with descriptive message on failure
4. Never throw — always return structured MCP content

## Testing

- Unit tests for each tool handler (mock the underlying functions)
- Integration test: spawn `ao serve` as child process, send JSON-RPC messages, verify responses
- Test error cases: missing file, invalid YAML, missing API key

## Scope Exclusions (Future Work)

- **MCP Resources** (exposing workflow files, output history) — v0.5
- **MCP Prompts** (pre-built prompt templates) — v0.5
- **HTTP/SSE transport** — when Web UI is built
- **Progress streaming** (step-by-step updates during run) — v0.5
- **resume_workflow tool** — v0.5

## Dependencies

- `@modelcontextprotocol/sdk` — Official MCP SDK for TypeScript
