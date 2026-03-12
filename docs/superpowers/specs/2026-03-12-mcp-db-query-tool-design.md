# MCP Database Query Tool -- Design Spec

## Overview

A generic, structured query tool (`db-query`) for the ExamCraft MCP Facade Server that enables arbitrary database queries via a JSON schema. The tool translates structured query parameters into safe SQLAlchemy queries -- no raw SQL is exposed.

## Motivation

The MCP server currently provides Fly.io infrastructure tools. Extending it with database access allows administrators to query application data directly from Claude (Desktop, Code, or claude.ai):

- Is a user currently logged in?
- Which users were active in a given time range?
- How many documents were uploaded since yesterday?
- What is the review status distribution across questions?

## Architecture

### Components

```
packages/premium/backend/mcp/
  tools/
    db_query.py            # DbQueryTool (MCP tool implementation)
  db/
    __init__.py
    schema_registry.py     # Table whitelist, field blacklist, metadata
    query_builder.py       # JSON -> SQLAlchemy query translation
```

### Data Flow

```
Claude sends db-query tool call
  -> DbQueryTool.execute()
    -> Superuser authorization check (token -> email -> User.is_superuser)
    -> SchemaRegistry validates table/field names
    -> QueryBuilder translates JSON to SQLAlchemy query
    -> Execute query against PostgreSQL (read-only)
    -> Serialize results (dates, UUIDs, enums)
  -> Return structured response via MCP transport
```

## Authorization

- The tool is restricted to superusers only
- Authorization flow: MCP auth token -> stored email (from OAuth flow) -> User lookup in DB -> check `User.is_superuser`
- Non-superusers receive an error: "Insufficient permissions: superuser access required"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "table": {
      "type": "string",
      "description": "Primary table to query"
    },
    "select": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Fields to return. Omit for all non-sensitive fields. Use table.field for joined queries."
    },
    "joins": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "table": {"type": "string"},
          "on": {
            "type": "object",
            "properties": {
              "left": {"type": "string"},
              "right": {"type": "string"}
            },
            "required": ["left", "right"]
          },
          "type": {
            "type": "string",
            "enum": ["inner", "left"],
            "default": "inner"
          }
        },
        "required": ["table", "on"]
      }
    },
    "where": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string"},
          "op": {
            "type": "string",
            "enum": ["eq", "neq", "gt", "gte", "lt", "lte", "like", "ilike", "in", "is_null", "is_not_null"]
          },
          "value": {}
        },
        "required": ["field", "op"]
      }
    },
    "group_by": {
      "type": "array",
      "items": {"type": "string"}
    },
    "aggregations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "func": {
            "type": "string",
            "enum": ["count", "sum", "avg", "min", "max"]
          },
          "field": {"type": "string"},
          "alias": {"type": "string"}
        },
        "required": ["func", "field", "alias"]
      }
    },
    "order_by": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string"},
          "direction": {
            "type": "string",
            "enum": ["asc", "desc"],
            "default": "asc"
          }
        },
        "required": ["field"]
      }
    },
    "having": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string", "description": "Aggregation alias or field"},
          "op": {
            "type": "string",
            "enum": ["eq", "neq", "gt", "gte", "lt", "lte"]
          },
          "value": {}
        },
        "required": ["field", "op", "value"]
      },
      "description": "Filter on aggregated results (SQL HAVING). Use aggregation aliases."
    },
    "limit": {
      "type": "integer",
      "default": 100,
      "maximum": 500
    },
    "offset": {
      "type": "integer",
      "default": 0,
      "description": "Number of rows to skip (for pagination)"
    }
  },
  "required": ["table"]
}
```

### Operators

| Operator | SQL Equivalent | Value Required |
|----------|---------------|----------------|
| `eq` | `=` | Yes |
| `neq` | `!=` | Yes |
| `gt` | `>` | Yes |
| `gte` | `>=` | Yes |
| `lt` | `<` | Yes |
| `lte` | `<=` | Yes |
| `like` | `LIKE` | Yes (pattern with %) |
| `ilike` | `ILIKE` | Yes (case-insensitive) |
| `in` | `IN` | Yes (array) |
| `is_null` | `IS NULL` | No |
| `is_not_null` | `IS NOT NULL` | No |

## Output Format

```json
{
  "columns": ["email", "status", "doc_count"],
  "rows": [
    {"email": "admin@talent-factory.ch", "status": "active", "doc_count": 12},
    {"email": "dozent@talent-factory.ch", "status": "active", "doc_count": 5}
  ],
  "row_count": 2,
  "total_available": 2,
  "truncated": false,
  "query_summary": "users LEFT JOIN documents, filtered by status='active', grouped by user, ordered by doc_count desc"
}
```

- `columns`: field names in result order (useful for empty results)
- `rows`: list of dicts with serialized values
- `row_count`: number of rows returned
- `total_available`: total matching rows (before limit)
- `truncated`: true if limit was applied and more rows exist
- `query_summary`: human-readable description of the executed query

## Security

### Table Whitelist

The registry auto-discovers all tables from `Base.metadata` at startup. The following tables are expected to be available:

- `users`, `user_sessions`, `audit_logs`, `documents`, `institutions`, `roles`, `user_roles`
- `question_reviews`, `review_comments`, `review_history`
- `prompts`, `prompt_usage_logs`
- `chat_sessions`, `chat_messages`
- `oauth_accounts`, `subscriptions`, `email_events`

New models added to the codebase are automatically queryable without MCP tool changes. The field blacklist (below) ensures sensitive fields remain protected regardless of table.

### Field Blacklist

The following fields are automatically excluded from all queries:

| Field | Table(s) | Reason |
|-------|----------|--------|
| `password_hash` | `users` | Credential |
| `password_reset_token` | `users` | Password reset secret |
| `email_verification_token` | `users` | Verification bypass risk |
| `access_token` | `oauth_accounts` | OAuth credential |
| `refresh_token` | `oauth_accounts` | OAuth credential |
| `token_jti` | `user_sessions` | Session secret |
| `refresh_token_jti` | `user_sessions` | Session secret |
| `provider_user_id` | `oauth_accounts` | External identity |
| `raw_user_info` | `oauth_accounts` | May contain tokens/PII |
| `stripe_subscription_id` | `subscriptions` | Payment secret |
| `stripe_customer_id` | `subscriptions` | Payment secret |
| `stripe_price_id` | `subscriptions` | Payment secret |

Queries that explicitly request blacklisted fields receive an error listing which fields are blocked.

### Additional Safeguards

- Read-only: only SELECT queries are possible by design (no INSERT/UPDATE/DELETE)
- All table and field names are validated against the schema registry before query construction
- Result limit enforced (max 500 rows)
- Superuser-only access via `User.is_superuser` flag

## Schema Registry

The `SchemaRegistry` reads SQLAlchemy model metadata to build a runtime catalog:

```python
class SchemaRegistry:
    def get_tables() -> list[str]
    def get_fields(table: str) -> list[FieldInfo]
    def is_field_allowed(table: str, field: str) -> bool
    def validate_table(table: str) -> None
    def validate_field(table: str, field: str) -> None
    def get_schema_description() -> dict  # For tools/list response
```

The registry is built once at startup from `Base.metadata` (SQLAlchemy declarative base). Auto-discovery ensures new models are queryable without MCP tool changes. The field blacklist is applied globally across all tables.

## Query Builder

The `QueryBuilder` translates the validated JSON structure into a SQLAlchemy query:

```python
class QueryBuilder:
    def __init__(self, registry: SchemaRegistry, session: Session)
    def build(self, query_params: dict) -> tuple[Query, str]
        # Returns (executable query, human-readable summary)
```

Build steps:
1. Resolve primary table from registry
2. Apply SELECT (or default to all allowed fields)
3. Apply JOINs with validated foreign key relationships
4. Apply WHERE filters with type-safe operator mapping
5. Apply GROUP BY
6. Apply aggregation functions
7. Apply HAVING filters on aggregated results
8. Apply ORDER BY
9. Compute `total_available` via separate COUNT query (before LIMIT/OFFSET)
10. Apply OFFSET and LIMIT

For grouped queries, `total_available` represents the number of groups (not individual rows before grouping).

Serialization handles: `datetime` -> ISO string, `UUID` -> string, `Enum` -> value, `None` -> null.

Type coercion: The `value` field in `where`/`having` clauses is untyped for flexibility. The QueryBuilder coerces values based on the target column type (e.g., string dates to `datetime`, string UUIDs to `UUID`). Invalid coercions produce a clear error message.

### Known Limitations

- JOINs support only simple equality conditions (`left = right`). Multi-condition joins are not supported.
- Only two JOIN types are available (`inner`, `left`). Full/right/cross joins are excluded for safety.

## Example Queries

### "Is user admin@talent-factory.ch currently logged in?"

```json
{
  "table": "user_sessions",
  "joins": [{"table": "users", "on": {"left": "user_sessions.user_id", "right": "users.id"}, "type": "inner"}],
  "select": ["users.email", "user_sessions.is_active", "user_sessions.expires_at"],
  "where": [
    {"field": "users.email", "op": "eq", "value": "admin@talent-factory.ch"},
    {"field": "user_sessions.is_active", "op": "eq", "value": true}
  ]
}
```

### "How many documents were uploaded since yesterday?"

```json
{
  "table": "documents",
  "where": [
    {"field": "created_at", "op": "gte", "value": "2026-03-11"}
  ],
  "aggregations": [
    {"func": "count", "field": "id", "alias": "total_uploads"}
  ]
}
```

### "Top 5 users by document count"

```json
{
  "table": "users",
  "joins": [{"table": "documents", "on": {"left": "users.id", "right": "documents.user_id"}, "type": "left"}],
  "select": ["users.email"],
  "aggregations": [{"func": "count", "field": "documents.id", "alias": "doc_count"}],
  "group_by": ["users.id", "users.email"],
  "order_by": [{"field": "doc_count", "direction": "desc"}],
  "limit": 5
}
```

## Integration

### BaseTool Refactoring

The existing `BaseTool` has a `fly_client` property that is irrelevant for `DbQueryTool`. Refactor `BaseTool` to make `fly_client` optional:

- Move the `fly_client` property from `BaseTool` into a `FlyBaseTool` subclass
- Existing Fly.io tools inherit from `FlyBaseTool` instead of `BaseTool`
- `DbQueryTool` inherits directly from `BaseTool`

This prevents failures when `FLY_API_TOKEN` is not configured (e.g., core-only deployments).

### Tool Registration

Register `DbQueryTool` in `tools/__init__.py` alongside existing Fly.io tools:

```python
from .db_query import DbQueryTool
_register(DbQueryTool())
```

### Database Session

The tool creates its own `SessionLocal()` instance per query execution, managed via try/finally to prevent connection leaks:

```python
db = SessionLocal()
try:
    result = query_builder.build_and_execute(params)
    return serialize(result)
finally:
    db.close()
```

### MCP Tool Description

The tool's `description` field should include a summary of available tables and their purposes, so Claude knows what data is queryable without needing a separate schema-discovery tool.
