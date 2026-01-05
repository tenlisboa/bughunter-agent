# Bug Triage Agent - MVP Specification

## Executive Summary

This document specifies a deep investigation agent that receives bug reports via webhook, analyzes source code autonomously, and produces accurate triage reports as Markdown files. The agent navigates codebases using a hybrid index (graph + vector embeddings) to trace error origins beyond the immediate stack trace.

This is a validation MVP focused on proving the core investigation logic works. External integrations (Jira, Slack) are deferred to a later phase.

### Key Characteristics

- **Diagnosis-focused**: Identifies root cause, does not suggest fixes
- **Precision over speed**: Up to 5 minutes per triage is acceptable
- **Multi-project**: Supports multiple repositories with isolated configurations
- **Stateless compute**: All configuration in YAML files, all state in PostgreSQL
- **File-based output**: Results written as Markdown for human review

---

## 1. Architecture Overview

```
                       ┌────────────────────┐
                       │  Webhook Receiver  │
    Datadog Webhook ──▶│     (FastAPI)      │
                       └──────────┬─────────┘
                                  │
                                  ▼
                       ┌────────────────────┐
                       │Triage Orchestrator │
                       │                    │
                       │ - Load config      │
                       │ - Check cache      │
                       │ - Sync index       │
                       │ - Run agent        │
                       │ - Write report     │
                       └──────────┬─────────┘
                                  │
                                  ▼
                       ┌────────────────────┐
                       │Investigation Agent │
                       │   (Gemini + Tools) │
                       └──────────┬─────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
       ┌────────────────┐ ┌─────────────┐ ┌───────────────┐
       │   PostgreSQL   │ │   GitHub    │ │ Local Storage │
       │(pgvector + AGE)│ │     API     │ │  (outputs/)   │
       │                │ │             │ │               │
       │ - Code index   │ │ - Files     │ │ - Reports.md  │
       │ - Graph rels   │ │ - Commits   │ │ - Traces.json │
       │ - Bug cache    │ │             │ │               │
       └────────────────┘ └─────────────┘ └───────────────┘
```

---

## 2. Project Configuration

Each repository is configured via a YAML file. These files are stored in a dedicated config repository or directory, loaded at runtime.

### 2.1 Configuration Schema

```yaml
# config/projects/px-backend.yaml

project_id: "px-backend"
display_name: "PX Backend API"
enabled: true

repository:
  provider: "github"
  owner: "pxbrasil"
  name: "backend"
  default_branch: "main"
  auth_secret_key: "GITHUB_PAT_PX" # references env var or secret manager

languages:
  primary: "php"
  secondary: ["go", "python"]

indexing:
  include_paths:
    - "src/"
    - "app/"
    - "lib/"
  exclude_paths:
    - "vendor/"
    - "node_modules/"
    - "tests/fixtures/"
    - "*.min.js"

output:
  directory: "triages/px-backend" # relative to output bucket/folder
  format: "markdown" # markdown or json

triage:
  max_iterations: 3 # agent investigation depth
  confidence_threshold: 0.7 # minimum confidence to auto-create ticket
  timeout_seconds: 300 # 5 minutes max

bug_filter:
  min_occurrences: 1 # process on first occurrence
  severity_levels: ["critical"] # only critical bugs
  ignore_patterns:
    - "HealthCheckException"
    - "RateLimitExceeded"

ownership:
  # Maps code paths to teams for assignment
  rules:
    - pattern: "src/Payment/*"
      team: "squad-financeiro"
    - pattern: "src/Qualification/*"
      team: "squad-onboarding"
    - pattern: "*"
      team: "squad-platform"
```

### 2.2 Global Configuration

```yaml
# config/global.yaml

database:
  host: "${DB_HOST}"
  port: 5432
  name: "bug_triage"

llm:
  provider: "google"
  model: "gemini-1.5-pro"
  temperature: 0.1 # low temperature for precision
  max_tokens: 8192

output:
  type: "local"
  local_path: "./outputs"

cache:
  bug_dedup_ttl_hours: 24 # same bug fingerprint within 24h = skip
  index_check_interval_seconds: 0 # check on every request (hash-based)

defaults:
  max_iterations: 3
  timeout_seconds: 300
  confidence_threshold: 0.7
```

---

## 3. Data Model

### 3.1 PostgreSQL 16 Schema

```sql
-- PostgreSQL 16 with extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;

-- Load AGE
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

---------------------------------------------------
-- RELATIONAL TABLES
---------------------------------------------------

-- Project sync state
CREATE TABLE project_sync_state (
    project_id VARCHAR(100) PRIMARY KEY,
    last_commit_hash VARCHAR(40) NOT NULL,
    last_indexed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    file_count INTEGER NOT NULL,
    symbol_count INTEGER NOT NULL
);

-- Code symbols (functions, classes, methods)
CREATE TABLE code_symbols (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(100) NOT NULL,
    qualified_name VARCHAR(500) NOT NULL,       -- e.g., "App\Services\PaymentService::process"
    symbol_type VARCHAR(50) NOT NULL,           -- function, method, class, trait, interface
    file_path VARCHAR(500) NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    signature TEXT,                             -- function signature with params
    docstring TEXT,
    source_code TEXT NOT NULL,
    embedding vector(768),                      -- Gemini embedding dimension

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(project_id, qualified_name)
);

CREATE INDEX idx_symbols_project ON code_symbols(project_id);
CREATE INDEX idx_symbols_file ON code_symbols(project_id, file_path);
CREATE INDEX idx_symbols_embedding ON code_symbols USING ivfflat (embedding vector_cosine_ops);

-- Bug processing cache (deduplication)
CREATE TABLE bug_cache (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(64) NOT NULL,           -- SHA256 of normalized bug signature
    project_id VARCHAR(100) NOT NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,
    output_path VARCHAR(500),                   -- path to generated .md file
    triage_result JSONB,

    UNIQUE(project_id, fingerprint)
);

CREATE INDEX idx_bug_cache_lookup ON bug_cache(project_id, fingerprint);

-- Triage history (audit log)
CREATE TABLE triage_history (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(100) NOT NULL,
    bug_fingerprint VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    triage_result JSONB NOT NULL,
    investigation_trace JSONB NOT NULL,         -- full agent reasoning trace
    output_path VARCHAR(500),                   -- path to generated .md file
    duration_seconds FLOAT NOT NULL,
    iterations_used INTEGER NOT NULL,
    confidence_score FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

---------------------------------------------------
-- GRAPH (Apache AGE)
---------------------------------------------------

-- Create graph for code relationships
SELECT create_graph('code_graph');

-- Vertex labels (created implicitly, but documented here):
-- (:Symbol {project_id, qualified_name, symbol_type, file_path})
-- (:File {project_id, path})
-- (:Module {project_id, name})

-- Edge labels:
-- [:CALLS {project_id, line_number}]        -- function/method calls
-- [:IMPORTS {project_id}]                   -- import/require/use statements
-- [:EXTENDS {project_id}]                   -- class inheritance
-- [:IMPLEMENTS {project_id}]                -- interface implementation
-- [:CONTAINS {project_id}]                  -- file contains symbol, module contains file
-- [:USES_TYPE {project_id}]                 -- type references in signatures
```

### 3.2 Graph Operations

```sql
-- Example: Find all callers of a function
SELECT * FROM cypher('code_graph', $$
    MATCH (caller:Symbol)-[:CALLS]->(target:Symbol {qualified_name: 'PaymentService::process'})
    WHERE caller.project_id = 'px-backend'
    RETURN caller.qualified_name, caller.file_path, caller.symbol_type
$$) AS (name agtype, file agtype, type agtype);

-- Example: Trace call path from entry point to error location
SELECT * FROM cypher('code_graph', $$
    MATCH path = (entry:Symbol)-[:CALLS*1..5]->(error:Symbol {qualified_name: 'ValidationUtil::validate'})
    WHERE entry.project_id = 'px-backend'
    RETURN path
    LIMIT 10
$$) AS (path agtype);

-- Example: Find all symbols in a file
SELECT * FROM cypher('code_graph', $$
    MATCH (f:File {path: 'src/Services/PaymentService.php'})-[:CONTAINS]->(s:Symbol)
    WHERE f.project_id = 'px-backend'
    RETURN s.qualified_name, s.symbol_type, s.line_start
$$) AS (name agtype, type agtype, line agtype);
```

---

## 4. Indexing Pipeline

### 4.1 Index Sync Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                       INDEX SYNC FLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │ Bug arrives  │────▶│ Check sync   │────▶│ HEAD hash same?  │    │
│  └──────────────┘     │ state table  │     └────────┬─────────┘    │
│                       └──────────────┘              │               │
│                                                     │               │
│                              ┌──────────────────────┴────────┐      │
│                              │                               │      │
│                              ▼                               ▼      │
│                       ┌─────────────┐                 ┌───────────┐ │
│                       │    YES      │                 │    NO     │ │
│                       │ Skip sync   │                 │ Run sync  │ │
│                       └─────────────┘                 └─────┬─────┘ │
│                                                             │       │
│                                                             ▼       │
│                                              ┌─────────────────────┐│
│                                              │  Git diff to find   ││
│                                              │  changed files      ││
│                                              └──────────┬──────────┘│
│                                                         │           │
│                                                         ▼           │
│                                              ┌─────────────────────┐│
│                                              │  Re-parse changed   ││
│                                              │  files only         ││
│                                              └──────────┬──────────┘│
│                                                         │           │
│                                                         ▼           │
│                                              ┌─────────────────────┐│
│                                              │  Update symbols,    ││
│                                              │  graph edges,       ││
│                                              │  embeddings         ││
│                                              └─────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Parser Strategy by Language

| Language | Parser                            | Symbol Extraction                               |
| -------- | --------------------------------- | ----------------------------------------------- |
| PHP      | tree-sitter-php                   | Classes, methods, functions, traits, interfaces |
| Go       | tree-sitter-go                    | Functions, methods, structs, interfaces         |
| Node.js  | tree-sitter-javascript/typescript | Functions, classes, methods, arrow functions    |
| Python   | tree-sitter-python                | Functions, classes, methods, async functions    |

### 4.3 Relation Extraction

| Relation Type | Detection Method                                |
| ------------- | ----------------------------------------------- |
| CALLS         | Static analysis of function/method calls in AST |
| IMPORTS       | Parse import/require/use statements             |
| EXTENDS       | Class inheritance declarations                  |
| IMPLEMENTS    | Interface implementation declarations           |
| USES_TYPE     | Type hints in function signatures, return types |

### 4.4 Indexer Component

```python
# Pseudocode for indexer structure

class CodeIndexer:
    def __init__(self, project_config: ProjectConfig, db: Database):
        self.config = project_config
        self.db = db
        self.github = GitHubClient(project_config.repository)
        self.parsers = {
            'php': TreeSitterPHP(),
            'go': TreeSitterGo(),
            'javascript': TreeSitterJS(),
            'python': TreeSitterPython(),
        }
        self.embedder = GeminiEmbedder()

    async def sync_if_needed(self) -> SyncResult:
        """Check if index needs update, sync incrementally if so."""
        current_hash = await self.github.get_head_hash()
        stored_state = await self.db.get_sync_state(self.config.project_id)

        if stored_state and stored_state.last_commit_hash == current_hash:
            return SyncResult(skipped=True, reason="hash_match")

        if stored_state is None:
            # Full initial index
            return await self._full_index(current_hash)
        else:
            # Incremental update
            changed_files = await self.github.get_changed_files(
                from_hash=stored_state.last_commit_hash,
                to_hash=current_hash
            )
            return await self._incremental_index(current_hash, changed_files)

    async def _parse_file(self, path: str, content: str) -> ParseResult:
        """Parse a single file, extract symbols and relations."""
        language = self._detect_language(path)
        parser = self.parsers.get(language)

        if not parser:
            return ParseResult.empty()

        tree = parser.parse(content)
        symbols = parser.extract_symbols(tree, path)
        relations = parser.extract_relations(tree, path)

        return ParseResult(symbols=symbols, relations=relations)

    async def _update_index(self, parse_results: list[ParseResult], commit_hash: str):
        """Update database with parsed results."""
        async with self.db.transaction():
            for result in parse_results:
                # Upsert symbols
                for symbol in result.symbols:
                    embedding = await self.embedder.embed(symbol.source_code)
                    await self.db.upsert_symbol(symbol, embedding)

                # Update graph edges
                for relation in result.relations:
                    await self.db.upsert_graph_edge(relation)

            # Update sync state
            await self.db.update_sync_state(
                project_id=self.config.project_id,
                commit_hash=commit_hash,
                file_count=...,
                symbol_count=...
            )
```

---

## 5. Bug Processing Pipeline

### 5.1 Webhook Payload (Datadog)

```json
{
  "id": "1234567890",
  "title": "Error: NullPointerException in PaymentService",
  "alert_type": "error",
  "priority": "critical",
  "tags": ["env:production", "service:px-backend", "version:2.3.1"],
  "body": {
    "error_class": "NullPointerException",
    "error_message": "Cannot call method on null",
    "stack_trace": [
      {
        "file": "src/Services/PaymentService.php",
        "line": 145,
        "function": "process",
        "class": "App\\Services\\PaymentService"
      },
      {
        "file": "src/Utils/ValidationUtil.php",
        "line": 67,
        "function": "validate",
        "class": "App\\Utils\\ValidationUtil"
      },
      {
        "file": "src/Http/Controllers/PaymentController.php",
        "line": 34,
        "function": "store",
        "class": "App\\Http\\Controllers\\PaymentController"
      }
    ],
    "context": {
      "user_id": "12345",
      "request_path": "/api/v1/payments",
      "request_method": "POST"
    }
  },
  "date_happened": 1699900000
}
```

### 5.2 Bug Fingerprinting

To deduplicate bugs, generate a fingerprint from stable attributes:

```python
def generate_fingerprint(bug: BugReport) -> str:
    """Generate stable fingerprint for deduplication."""
    components = [
        bug.error_class,
        bug.error_message_normalized,  # remove variable parts like IDs
        # Top 3 stack frames (file + function only, not line numbers)
        *[f"{frame.file}:{frame.function}" for frame in bug.stack_trace[:3]]
    ]
    content = "|".join(components)
    return hashlib.sha256(content.encode()).hexdigest()
```

### 5.3 Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUG PROCESSING FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐                                                            │
│  │  Webhook    │                                                            │
│  │  received   │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────┐                            │
│  │  1. Parse payload, identify project         │                            │
│  │     (from service tag or explicit field)    │                            │
│  └──────────────────────┬──────────────────────┘                            │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐      ┌──────────────────┐  │
│  │  2. Load project config                     │─────▶│  Config not      │  │
│  │     (from YAML file)                        │      │  found? 404      │  │
│  └──────────────────────┬──────────────────────┘      └──────────────────┘  │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐      ┌──────────────────┐  │
│  │  3. Apply bug filters                       │─────▶│  Filtered out?   │  │
│  │     (severity, patterns, occurrences)       │      │  200 + skip      │  │
│  └──────────────────────┬──────────────────────┘      └──────────────────┘  │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐      ┌──────────────────┐  │
│  │  4. Check bug cache (fingerprint)           │─────▶│  Already seen?   │  │
│  │                                             │      │  200 + increment │  │
│  └──────────────────────┬──────────────────────┘      │  counter only    │  │
│                         │                             └──────────────────┘  │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐                            │
│  │  5. Sync code index if needed               │                            │
│  │     (check HEAD hash)                       │                            │
│  └──────────────────────┬──────────────────────┘                            │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐                            │
│  │  6. Run Investigation Agent                 │                            │
│  │     (up to N iterations)                    │                            │
│  └──────────────────────┬──────────────────────┘                            │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐      ┌──────────────────┐  │
│  │  7. Check confidence threshold              │─────▶│  Below threshold?│  │
│  │                                             │      │  Flag in output  │  │
│  └──────────────────────┬──────────────────────┘      └──────────────────┘  │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐                            │
│  │  8. Write triage report (.md)               │                            │
│  │     (to local filesystem)                   │                            │
│  └──────────────────────┬──────────────────────┘                            │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────┐                            │
│  │  9. Store in cache + history                │                            │
│  │      Return 200                             │                            │
│  └─────────────────────────────────────────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Investigation Agent

### 6.1 Agent Design

The agent uses a ReAct-style loop with access to code navigation tools. It reasons about the bug, formulates hypotheses, and uses tools to validate or refine them.

### 6.2 Available Tools

| Tool                  | Description                                       | Input                            | Output                                   |
| --------------------- | ------------------------------------------------- | -------------------------------- | ---------------------------------------- |
| `read_file`           | Read file content, optionally specific line range | `{path, start_line?, end_line?}` | File content with line numbers           |
| `search_code`         | Semantic search across codebase                   | `{query, limit?}`                | List of relevant symbols with snippets   |
| `get_symbol`          | Get full details of a specific symbol             | `{qualified_name}`               | Symbol with source, signature, docstring |
| `get_callers`         | Find all functions that call a given symbol       | `{qualified_name}`               | List of caller symbols                   |
| `get_callees`         | Find all functions called by a given symbol       | `{qualified_name}`               | List of called symbols                   |
| `get_definition`      | Find where a symbol is defined                    | `{name}`                         | Symbol definition location               |
| `get_implementations` | Find implementations of interface/trait           | `{qualified_name}`               | List of implementing classes             |
| `get_recent_commits`  | Get recent commits affecting a file               | `{path, days?}`                  | List of commits with messages            |
| `get_file_symbols`    | List all symbols in a file                        | `{path}`                         | List of symbols in file                  |

### 6.3 Tool Implementations

```python
class AgentTools:
    def __init__(self, project_id: str, db: Database, github: GitHubClient):
        self.project_id = project_id
        self.db = db
        self.github = github

    async def read_file(self, path: str, start_line: int = None, end_line: int = None) -> str:
        """Fetch file from GitHub, optionally slice to line range."""
        content = await self.github.get_file_content(path)
        lines = content.split('\n')

        if start_line is not None:
            lines = lines[start_line - 1 : end_line or len(lines)]
            # Add line numbers for context
            return '\n'.join(f"{i + start_line}: {line}" for i, line in enumerate(lines))

        return content

    async def search_code(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Semantic search using vector similarity."""
        embedding = await self.embedder.embed(query)

        results = await self.db.query("""
            SELECT qualified_name, file_path, line_start, line_end,
                   signature, source_code,
                   1 - (embedding <=> $1) as similarity
            FROM code_symbols
            WHERE project_id = $2
            ORDER BY embedding <=> $1
            LIMIT $3
        """, embedding, self.project_id, limit)

        return [SearchResult(**r) for r in results]

    async def get_callers(self, qualified_name: str) -> list[Symbol]:
        """Query graph for incoming CALLS edges."""
        results = await self.db.query_graph("""
            SELECT * FROM cypher('code_graph', $$
                MATCH (caller:Symbol)-[c:CALLS]->(target:Symbol {qualified_name: $name})
                WHERE caller.project_id = $project_id
                RETURN caller.qualified_name as name,
                       caller.file_path as file,
                       caller.line_start as line,
                       c.line_number as call_line
            $$) AS (name agtype, file agtype, line agtype, call_line agtype)
        """, name=qualified_name, project_id=self.project_id)

        return [Symbol(**r) for r in results]

    async def get_callees(self, qualified_name: str) -> list[Symbol]:
        """Query graph for outgoing CALLS edges."""
        results = await self.db.query_graph("""
            SELECT * FROM cypher('code_graph', $$
                MATCH (source:Symbol {qualified_name: $name})-[c:CALLS]->(callee:Symbol)
                WHERE source.project_id = $project_id
                RETURN callee.qualified_name as name,
                       callee.file_path as file,
                       callee.line_start as line,
                       c.line_number as call_line
            $$) AS (name agtype, file agtype, line agtype, call_line agtype)
        """, name=qualified_name, project_id=self.project_id)

        return [Symbol(**r) for r in results]

    async def get_recent_commits(self, path: str, days: int = 7) -> list[Commit]:
        """Get commits from GitHub API."""
        since = datetime.utcnow() - timedelta(days=days)
        return await self.github.get_commits(path=path, since=since)
```

### 6.4 Agent Loop

```python
class InvestigationAgent:
    def __init__(
        self,
        config: ProjectConfig,
        tools: AgentTools,
        llm: GeminiClient
    ):
        self.config = config
        self.tools = tools
        self.llm = llm
        self.max_iterations = config.triage.max_iterations

    async def investigate(self, bug: BugReport) -> TriageResult:
        """Run investigation loop until confident or max iterations."""

        context = InvestigationContext(
            bug=bug,
            findings=[],
            hypotheses=[],
            visited_files=set(),
            visited_symbols=set()
        )

        for iteration in range(self.max_iterations):
            # Generate next action based on current context
            action = await self._plan_next_action(context, iteration)

            if action.type == "conclude":
                break

            # Execute tool
            result = await self._execute_tool(action.tool, action.params)

            # Update context with findings
            context.findings.append(Finding(
                iteration=iteration,
                tool=action.tool,
                params=action.params,
                result=result,
                reasoning=action.reasoning
            ))

        # Generate final triage result
        return await self._synthesize_result(context)

    async def _plan_next_action(
        self,
        context: InvestigationContext,
        iteration: int
    ) -> AgentAction:
        """Ask LLM to decide next investigation step."""

        prompt = self._build_planning_prompt(context, iteration)

        response = await self.llm.generate(
            prompt,
            temperature=0.1,  # Low temperature for consistency
            response_format=AgentActionSchema
        )

        return AgentAction.parse(response)

    async def _synthesize_result(self, context: InvestigationContext) -> TriageResult:
        """Generate final triage from investigation context."""

        prompt = self._build_synthesis_prompt(context)

        response = await self.llm.generate(
            prompt,
            temperature=0.1,
            response_format=TriageResultSchema
        )

        result = TriageResult.parse(response)
        result.investigation_trace = context.to_trace()

        return result
```

### 6.5 System Prompt

```
You are a senior software engineer investigating a production bug. Your goal is to identify the root cause with high precision.

## Your Task
Given a bug report with stack trace, investigate the codebase to determine:
1. The immediate cause of the error
2. The root cause (which may be upstream from the error location)
3. Which component/team owns the problematic code
4. Severity assessment

## Investigation Strategy
1. Start by examining the error location in the stack trace
2. Trace data flow upstream - where do the problematic values come from?
3. Check for recent changes to relevant files
4. Look for patterns - is this a common type of bug?

## Available Tools
{tool_descriptions}

## Guidelines
- Be methodical. Examine evidence before forming conclusions.
- Use get_callers to trace upstream when you suspect bad input data.
- Use search_code when you need to find related code by concept.
- Check recent commits when you suspect a regression.
- Stop when you have high confidence in the root cause, or after exhausting useful leads.

## Output Format
After each tool use, explain:
- What you learned
- How it updates your hypotheses
- What you want to investigate next (or why you're ready to conclude)

When concluding, provide:
- Root cause description
- Evidence supporting your conclusion
- Confidence level (0-1)
- Suggested owner based on code location
```

### 6.6 Example Investigation Trace

```json
{
  "bug": {
    "error_class": "NullPointerException",
    "error_message": "Cannot call method process() on null",
    "stack_trace": [
      {
        "file": "src/Services/PaymentService.php",
        "line": 145,
        "function": "process"
      },
      {
        "file": "src/Controllers/PaymentController.php",
        "line": 34,
        "function": "store"
      }
    ]
  },
  "iterations": [
    {
      "iteration": 0,
      "reasoning": "Starting at the error location to understand what's null",
      "tool": "read_file",
      "params": {
        "path": "src/Services/PaymentService.php",
        "start_line": 140,
        "end_line": 155
      },
      "result": "140: public function process(Transaction $transaction)\n141: {\n142:     $validator = $this->validatorFactory->create($transaction->type);\n143:     \n144:     // NPE happens here - $validator is null\n145:     $result = $validator->process($transaction);\n...",
      "finding": "The validator returned from factory is null. Need to check validatorFactory->create()"
    },
    {
      "iteration": 1,
      "reasoning": "Need to see how validatorFactory->create() works and when it returns null",
      "tool": "get_definition",
      "params": { "name": "ValidatorFactory::create" },
      "result": {
        "qualified_name": "App\\Factories\\ValidatorFactory::create",
        "file": "src/Factories/ValidatorFactory.php",
        "line": 23
      },
      "finding": "Found the factory. Will read the implementation."
    },
    {
      "iteration": 2,
      "reasoning": "Reading the factory to understand null return conditions",
      "tool": "read_file",
      "params": {
        "path": "src/Factories/ValidatorFactory.php",
        "start_line": 20,
        "end_line": 45
      },
      "result": "23: public function create(string $type): ?Validator\n24: {\n25:     return match($type) {\n26:         'credit_card' => new CreditCardValidator(),\n27:         'pix' => new PixValidator(),\n28:         'boleto' => new BoletoValidator(),\n29:         default => null  // Returns null for unknown types!\n30:     };\n31: }",
      "finding": "Factory returns null for unknown transaction types. The match expression has no handler for some type. Need to check what type is being passed."
    }
  ],
  "conclusion": {
    "root_cause": "ValidatorFactory::create() returns null for transaction types not in the match expression. A new transaction type was likely introduced without updating the factory.",
    "evidence": [
      "Line 29 of ValidatorFactory.php explicitly returns null for unmatched types",
      "PaymentService.php does not check for null before calling process()"
    ],
    "confidence": 0.85,
    "owner": "squad-financeiro",
    "severity": "critical"
  }
}
```

---

## 7. Output: Triage Reports

### 7.1 Output File Structure

Each triage generates two files:

- `{timestamp}_{fingerprint}.md` - Human-readable report
- `{timestamp}_{fingerprint}.json` - Machine-readable trace (for debugging/evaluation)

### 7.2 Markdown Report Template

```markdown
# Bug Triage Report

**Generated**: 2024-01-15T10:30:00Z  
**Project**: px-backend  
**Confidence**: 85%  
**Suggested Owner**: squad-financeiro

---

## Error Summary

| Field       | Value                                |
| ----------- | ------------------------------------ |
| Error Class | NullPointerException                 |
| Message     | Cannot call method process() on null |
| First Seen  | 2024-01-15T10:25:00Z                 |
| Occurrences | 1                                    |

## Stack Trace
```

src/Services/PaymentService.php:145 in process()
src/Controllers/PaymentController.php:34 in store()

```

---

## Root Cause Analysis

ValidatorFactory::create() returns null for transaction types not in the match
expression. A new transaction type was likely introduced without updating the factory.

The factory at `src/Factories/ValidatorFactory.php:29` explicitly returns null
for unmatched types, and `PaymentService.php` does not check for null before
calling `process()`.

## Evidence

1. **ValidatorFactory.php:29** - `default => null` in match expression
2. **PaymentService.php:145** - No null check before `$validator->process()`
3. Recent commit `abc123` (3 days ago) added new transaction type without factory update

## Affected Files

- `src/Services/PaymentService.php`
- `src/Factories/ValidatorFactory.php`
- `src/Controllers/PaymentController.php`

## Investigation Trace

| Step | Tool | Finding |
|------|------|---------|
| 1 | read_file | Examined error location, found null validator |
| 2 | get_definition | Located ValidatorFactory::create |
| 3 | read_file | Found match expression returns null for unknown types |

---

*Generated by Bug Triage Agent v1.0*
```

### 7.3 Output Writer

```python
class TriageOutputWriter:
    def __init__(self, config: OutputConfig):
        self.config = config
        self.storage = LocalStorage(config.local_path)

    async def write(
        self,
        project_id: str,
        triage: TriageResult,
        bug: BugReport,
        trace: InvestigationTrace
    ) -> str:
        """Write triage report and return output path."""

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fingerprint_short = bug.fingerprint[:8]
        base_name = f"{timestamp}_{fingerprint_short}"

        # Get project output directory
        project_config = load_project_config(project_id)
        output_dir = project_config.output.directory

        # Write markdown report
        md_content = self._render_markdown(triage, bug, trace)
        md_path = f"{output_dir}/{base_name}.md"
        await self.storage.write(md_path, md_content)

        # Write JSON trace
        json_content = json.dumps({
            "bug": bug.dict(),
            "triage": triage.dict(),
            "trace": trace.dict()
        }, indent=2, default=str)
        json_path = f"{output_dir}/{base_name}.json"
        await self.storage.write(json_path, json_content)

        return md_path

    def _render_markdown(
        self,
        triage: TriageResult,
        bug: BugReport,
        trace: InvestigationTrace
    ) -> str:
        """Render markdown report from template."""
        template = self._load_template()
        return template.render(
            triage=triage,
            bug=bug,
            trace=trace,
            generated_at=datetime.utcnow().isoformat()
        )


class LocalStorage:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    async def write(self, path: str, content: str):
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
```

### 7.4 Output Directory Structure

```
outputs/
├── px-backend/
│   ├── 20240115_103000_a1b2c3d4.md
│   ├── 20240115_103000_a1b2c3d4.json
│   ├── 20240115_143022_e5f6g7h8.md
│   └── 20240115_143022_e5f6g7h8.json
├── px-driver-app/
│   └── ...
└── px-shipper-api/
    └── ...
```

```

---

## 8. API Specification

### 8.1 Webhook Endpoint

```

POST /webhook/{project_id}
Content-Type: application/json

Request: Datadog webhook payload (see section 5.1)

Response 200 (processed):
{
"status": "processed",
"output_path": "triages/px-backend/20240115_103000_a1b2c3d4.md",
"triage": {
"root_cause": "...",
"confidence": 0.85,
"severity": "critical",
"owner": "squad-financeiro"
}
}

Response 200 (skipped - duplicate):
{
"status": "skipped",
"reason": "duplicate",
"existing_output": "triages/px-backend/20240115_090000_a1b2c3d4.md",
"occurrence_count": 5
}

Response 200 (skipped - filtered):
{
"status": "skipped",
"reason": "filtered",
"filter": "severity_level"
}

Response 404 (project not found):
{
"error": "project_not_found",
"message": "No configuration found for project: unknown-project"
}

Response 500 (processing error):
{
"error": "processing_error",
"message": "...",
"trace_id": "abc123"
}

```

### 8.2 Health Endpoint

```

GET /health

Response 200:
{
"status": "healthy",
"database": "connected",
"version": "1.0.0"
}

```

### 8.3 Manual Trigger (for testing)

```

POST /triage
Content-Type: application/json

Request:
{
"project_id": "px-backend",
"error_class": "NullPointerException",
"error_message": "...",
"stack_trace": [...],
"dry_run": true // optional: don't write output files
}

Response: Same as webhook endpoint

```

### 8.4 List Triages (for review)

```

GET /triages/{project_id}?limit=20&since=2024-01-01

Response 200:
{
"triages": [
{
"fingerprint": "a1b2c3d4...",
"output_path": "triages/px-backend/20240115_103000_a1b2c3d4.md",
"error_class": "NullPointerException",
"confidence": 0.85,
"owner": "squad-financeiro",
"created_at": "2024-01-15T10:30:00Z"
}
],
"total": 42
}

````

---

## 9. Project Structure

```
bug-triage-agent/
├── src/
│   ├── main.py                      # FastAPI app, endpoints
│   ├── config/
│   │   ├── loader.py                # YAML config loading
│   │   └── schemas.py               # Pydantic config models
│   ├── core/
│   │   ├── orchestrator.py          # Main processing pipeline
│   │   ├── agent.py                 # Investigation agent loop
│   │   ├── tools.py                 # Agent tools implementation
│   │   └── prompts.py               # LLM prompt templates
│   ├── indexing/
│   │   ├── indexer.py               # Code indexer
│   │   ├── parsers/
│   │   │   ├── base.py
│   │   │   ├── php.py
│   │   │   ├── go.py
│   │   │   ├── javascript.py
│   │   │   └── python.py
│   │   └── embedder.py              # Gemini embeddings
│   ├── integrations/
│   │   ├── github.py                # GitHub API client
│   │   └── datadog.py               # Webhook payload parsing
│   ├── output/
│   │   ├── writer.py                # Triage report writer
│   │   ├── storage.py               # Local storage
│   │   └── templates/
│   │       └── triage_report.md.j2  # Jinja2 template
│   ├── db/
│   │   ├── connection.py
│   │   ├── repositories.py          # Data access layer
│   │   └── migrations/
│   └── models/
│       ├── bug.py                   # BugReport, BugFingerprint
│       ├── triage.py                # TriageResult, Finding
│       └── code.py                  # Symbol, Relation
├── config/
│   ├── global.yaml
│   └── projects/
│       ├── px-backend.yaml
│       ├── px-driver-app.yaml
│       └── px-shipper-api.yaml
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── sample_bugs/
├── scripts/
│   ├── init_db.py                   # Database setup
│   ├── index_project.py             # Manual indexing trigger
│   └── test_triage.py               # Manual triage testing
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 10. Testing Strategy

### 10.1 Test Categories

| Category    | Scope                                      | Tools                      |
| ----------- | ------------------------------------------ | -------------------------- |
| Unit        | Parsers, fingerprinting, prompt formatting | pytest                     |
| Integration | Database queries, GitHub API               | pytest + testcontainers    |
| Agent       | Full investigation loop with mocked tools  | pytest + recorded fixtures |
| E2E         | Webhook to ticket creation                 | Staging environment        |

### 10.2 Agent Testing Approach

Use recorded bug scenarios with expected outcomes:

```python
# tests/fixtures/sample_bugs/null_pointer_payment.json
{
    "bug": { ... },
    "expected_triage": {
        "root_cause_contains": ["ValidatorFactory", "null", "unknown type"],
        "severity": "critical",
        "confidence_min": 0.7,
        "owner": "squad-financeiro"
    }
}
```

### 10.3 Evaluation Metrics

Track over time:

- **Precision**: % of triages that correctly identify root cause (human review)
- **Iteration efficiency**: Average iterations to reach conclusion
- **Time to triage**: End-to-end latency
- **Cache hit rate**: % of bugs deduplicated

---

## 11. Future Enhancements (Post-MVP)

The following are explicitly out of scope for MVP but documented for future consideration:

### Phase 2: Integrations

1. **Jira integration**: Create tickets automatically from triage results
2. **Slack notifications**: Alert channels on new triages
3. **PagerDuty**: Escalate critical bugs to on-call

### Phase 3: Advanced Features

4. **Fix suggestions**: Agent proposes code changes, not just diagnosis
5. **Multi-repo tracing**: Follow bugs across service boundaries
6. **Log integration**: Include application logs in investigation context
7. **Learning from feedback**: Incorporate human corrections to improve
8. **Proactive detection**: Find potential bugs before they manifest
9. **PR integration**: Comment on PRs that might introduce bugs
10. **Metrics dashboard**: Visualization of triage performance

---

## 12. Success Criteria

The MVP is considered successful when:

1. **Functional**: Processes webhooks from Datadog, writes triage reports to local filesystem
2. **Accurate**: >70% of triages correctly identify root cause (measured by human review)
3. **Reliable**: <5% error rate on bug processing
4. **Scalable**: Supports 3 projects without configuration changes to core code
5. **Maintainable**: Adding a new project requires only a YAML file
6. **Reviewable**: Output reports are clear enough for humans to validate and act on

---

## Appendix A: Required API Permissions

| Service | Permission               | Scope                    |
| ------- | ------------------------ | ------------------------ |
| GitHub  | `repo:read`              | Read repository contents |
| GitHub  | `metadata:read`          | Read commits, branches   |
| Gemini  | Text generation          | Standard API access      |
| Gemini  | Embeddings               | Standard API access      |

## Appendix B: Environment Variables

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bug_triage
DB_USER=triage_agent
DB_PASSWORD=***

# LLM
GEMINI_API_KEY=***

# GitHub (per project)
GITHUB_PAT_PX=***

# Output
OUTPUT_PATH=./outputs

# Application
LOG_LEVEL=INFO
```

## Appendix C: Future Integrations (Post-MVP)

When the core agent is validated, these integrations can be added:

1. **Jira** - Create tickets automatically from triage results
2. **Slack** - Notify channels on new triages
3. **PagerDuty** - Escalate critical bugs to on-call
4. **GitHub Issues** - Alternative to Jira for some projects
