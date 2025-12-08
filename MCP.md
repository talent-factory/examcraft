# MCP Server Configuration Guide

This document describes how to set up and configure MCP (Model Context Protocol) servers for Claude Code integration in the ExamCraft AI project.

## What is MCP?

MCP (Model Context Protocol) is an open standard protocol that connects Claude Code with external tools and services. In this project, we use MCP servers for:

- **Task Master AI**: AI-powered task management and project planning
- **Linear**: Issue tracking and project management integration

## Quick Start

### 1. Prerequisites

- Claude Code installed and configured
- Node.js 18+ (for npx-based MCP servers)
- API keys for the services you want to integrate

### 2. Set Up Environment Variables

Copy the MCP configuration template:

```bash
# Copy the template (if not already done)
cp .mcp.json.template .mcp.json

# The .env file should already contain MCP variables from .env.example
# Update the following variables in your .env or shell profile:
export ANTHROPIC_API_KEY="sk-ant-api03-your_key_here"  # pragma: allowlist secret
export LINEAR_API_KEY="lin_api_your_key_here"  # pragma: allowlist secret
```

**IMPORTANT**: Never commit API keys to git! The `.mcp.json` file is already in `.gitignore`.

### 3. Get API Keys

#### Anthropic API Key

1. Visit https://console.anthropic.com/
2. Go to "API Keys" section
3. Create a new API key
4. Copy the key (starts with `sk-ant-api03-`)

#### Linear API Key

1. Visit https://linear.app/settings/api
2. Create a new personal API key
3. Give it a descriptive name (e.g., "Claude Code Integration")
4. Copy the key (starts with `lin_api_`)

### 4. Verify MCP Server Configuration

```bash
# In Claude Code, check MCP server status:
/mcp

# Or list all configured servers:
claude mcp list
```

## MCP Configuration Details

### File: `.mcp.json`

This file contains the MCP server configurations with environment variable references:

```json
{
  "mcpServers": {
    "taskmaster-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    },
    "linear": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-linear"],
      "env": {
        "LINEAR_API_KEY": "${LINEAR_API_KEY}"
      }
    }
  }
}
```

**Key Points**:

- Uses `${VAR}` syntax for environment variable expansion
- Secrets are never stored in the JSON file
- Both servers use `npx` to run Node.js packages on-demand

### File: `.mcp.json.template`

This is a team-shared template for `.mcp.json`. Team members should:

1. Copy `.mcp.json.template` to `.mcp.json`
2. Set environment variables with their own API keys
3. Never commit `.mcp.json` (it's in `.gitignore`)

## Available MCP Tools

Once configured, the following tools are available in Claude Code:

### Task Master AI Tools

**Project Setup**:
- `mcp__taskmaster-ai__initialize_project` - Initialize Task Master structure
- `mcp__taskmaster-ai__models` - Get/set AI model configuration
- `mcp__taskmaster-ai__rules` - Add/remove rule profiles
- `mcp__taskmaster-ai__response_language` - Get/set response language

**Task Management**:
- `mcp__taskmaster-ai__get_tasks` - List all tasks (with filtering)
- `mcp__taskmaster-ai__get_task` - Get detailed task information
- `mcp__taskmaster-ai__next_task` - Find next task to work on
- `mcp__taskmaster-ai__add_task` - Create new tasks
- `mcp__taskmaster-ai__add_subtask` - Add subtask to existing task
- `mcp__taskmaster-ai__update_task` - Update single task
- `mcp__taskmaster-ai__update_subtask` - Update subtask information
- `mcp__taskmaster-ai__update` - Update multiple upcoming tasks
- `mcp__taskmaster-ai__set_task_status` - Change task status
- `mcp__taskmaster-ai__remove_task` - Delete task permanently
- `mcp__taskmaster-ai__remove_subtask` - Remove subtask from parent
- `mcp__taskmaster-ai__clear_subtasks` - Clear all subtasks
- `mcp__taskmaster-ai__move_task` - Move task to new position

**Task Complexity**:
- `mcp__taskmaster-ai__expand_task` - Expand task into subtasks
- `mcp__taskmaster-ai__expand_all` - Expand all pending tasks
- `mcp__taskmaster-ai__scope_up_task` - Increase task complexity
- `mcp__taskmaster-ai__scope_down_task` - Decrease task complexity
- `mcp__taskmaster-ai__analyze_project_complexity` - Analyze complexity
- `mcp__taskmaster-ai__complexity_report` - Display complexity report

**Dependencies**:
- `mcp__taskmaster-ai__add_dependency` - Add dependency relationship
- `mcp__taskmaster-ai__remove_dependency` - Remove dependency
- `mcp__taskmaster-ai__validate_dependencies` - Check for issues
- `mcp__taskmaster-ai__fix_dependencies` - Fix invalid dependencies

**Tags**:
- `mcp__taskmaster-ai__list_tags` - List all tags
- `mcp__taskmaster-ai__add_tag` - Create new tag
- `mcp__taskmaster-ai__delete_tag` - Delete tag and tasks
- `mcp__taskmaster-ai__use_tag` - Switch tag context
- `mcp__taskmaster-ai__rename_tag` - Rename existing tag
- `mcp__taskmaster-ai__copy_tag` - Copy tag with tasks

**TDD Workflow (Autopilot)**:
- `mcp__taskmaster-ai__autopilot_start` - Start TDD workflow
- `mcp__taskmaster-ai__autopilot_resume` - Resume workflow
- `mcp__taskmaster-ai__autopilot_next` - Get next action
- `mcp__taskmaster-ai__autopilot_status` - Get workflow status
- `mcp__taskmaster-ai__autopilot_complete_phase` - Complete TDD phase
- `mcp__taskmaster-ai__autopilot_commit` - Create git commit
- `mcp__taskmaster-ai__autopilot_finalize` - Finalize workflow
- `mcp__taskmaster-ai__autopilot_abort` - Abort workflow

**Other**:
- `mcp__taskmaster-ai__parse_prd` - Generate tasks from PRD document
- `mcp__taskmaster-ai__research` - AI-powered research queries
- `mcp__taskmaster-ai__generate` - Generate individual task files

### Linear Tools

- `mcp__linear__get_issue` - Get issue details
- `mcp__linear__list_issues` - List issues in team
- `mcp__linear__create_issue` - Create new issues
- `mcp__linear__update_issue` - Update issue status/properties
- `mcp__linear__list_issue_statuses` - List available issue statuses
- `mcp__linear__list_issue_labels` - List available labels
- `mcp__linear__create_issue_label` - Create new labels
- `mcp__linear__list_projects` - List projects
- `mcp__linear__get_project` - Get project details
- `mcp__linear__create_project` - Create new projects
- `mcp__linear__update_project` - Update project properties
- `mcp__linear__list_teams` - List available teams
- `mcp__linear__get_team` - Get team details
- `mcp__linear__list_users` - List users in workspace
- `mcp__linear__get_user` - Get user details
- `mcp__linear__list_comments` - List issue comments
- `mcp__linear__create_comment` - Create issue comments
- `mcp__linear__list_cycles` - List team cycles
- `mcp__linear__list_documents` - List Linear documents
- `mcp__linear__get_document` - Get document details
- `mcp__linear__search_documentation` - Search Linear docs

## Usage Examples

### Using Linear Integration

```bash
# In Claude Code conversation:
> Show me all issues in the Talent Factory team
> Get details for issue TF-177
> Update TF-177 status to "In Review"
```

### Using Task Master AI

```bash
# Initialize Task Master in project:
> Initialize the Task Master project structure

# Add a new task:
> Add a task to implement user authentication

# List all tasks:
> Show me all pending tasks
```

## Troubleshooting

### MCP Server Not Connecting

**Symptoms**: MCP tools not appearing in Claude Code

**Solutions**:

1. **Check environment variables are set**:

   ```bash
   echo $ANTHROPIC_API_KEY
   echo $LINEAR_API_KEY
   ```

   If empty, add to your shell profile (`~/.zshrc` or `~/.bashrc`):

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api03-..."  # pragma: allowlist secret
   export LINEAR_API_KEY="lin_api_..."  # pragma: allowlist secret
   ```

   Then reload: `source ~/.zshrc`

2. **Verify .mcp.json exists**:

   ```bash
   ls -la .mcp.json
   # Should exist and not be in git
   ```

3. **Test MCP server manually**:

   ```bash
   # Task Master AI
   npx -y --package=task-master-ai task-master-ai

   # Linear
   npx -y @modelcontextprotocol/server-linear
   ```

4. **Restart Claude Code**:

   ```bash
   # Exit Claude Code
   exit

   # Start again
   claude
   ```

5. **Check MCP status in Claude Code**:

   ```bash
   /mcp
   ```

### API Key Errors

**Symptoms**: "Unauthorized" or "Invalid API Key" errors

**Solutions**:

1. **Verify API key format**:
   - Anthropic: starts with `sk-ant-api03-`
   - Linear: starts with `lin_api_`

2. **Check API key validity**:
   - Anthropic: https://console.anthropic.com/
   - Linear: https://linear.app/settings/api

3. **Ensure no extra spaces/newlines**:

   ```bash
   # Wrong:
   export LINEAR_API_KEY=" lin_api_key "

   # Correct:
   export LINEAR_API_KEY="lin_api_key"  # pragma: allowlist secret
   ```

### NPM/npx Issues

**Symptoms**: MCP server fails to start with npx errors

**Solutions**:

1. **Update Node.js**:

   ```bash
   node --version  # Should be 18+
   ```

2. **Clear npx cache**:

   ```bash
   npx clear-npx-cache
   ```

3. **Manually install packages**:

   ```bash
   npm install -g task-master-ai
   npm install -g @modelcontextprotocol/server-linear
   ```

## Security Best Practices

### ✅ DO

- Store API keys in environment variables
- Use `.env` or shell profile for local keys
- Keep `.mcp.json` in `.gitignore`
- Share `.mcp.json.template` with team
- Rotate API keys periodically
- Use separate API keys per developer

### ❌ DON'T

- Commit `.mcp.json` with API keys to git
- Share API keys via chat/email
- Use production API keys for development
- Hardcode keys in JSON files
- Reuse API keys across multiple projects

## Advanced Configuration

### Adding Custom MCP Servers

To add a new MCP server:

1. **Update `.mcp.json`**:

   ```json
   {
     "mcpServers": {
       "my-custom-server": {
         "command": "npx",
         "args": ["-y", "@company/custom-mcp-server"],
         "env": {
           "CUSTOM_API_KEY": "${CUSTOM_API_KEY}"
         }
       }
     }
   }
   ```

2. **Add environment variable**:

   ```bash
   export CUSTOM_API_KEY="your_key_here"  # pragma: allowlist secret
   ```

3. **Update `.env.example`**:

   ```bash
   # Custom MCP Server
   CUSTOM_API_KEY=your_key_here
   ```

4. **Update `.mcp.json.template`** with the new server config

### HTTP/Remote MCP Servers

For HTTP-based MCP servers (less common):

```json
{
  "mcpServers": {
    "remote-service": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${REMOTE_API_KEY}"
      }
    }
  }
}
```

### MCP Server Scopes

MCP servers can be configured in three scopes:

| Scope | Config File | Usage |
|-------|-------------|-------|
| **local** | `~/.claude.json` | Personal experiments |
| **project** | `.mcp.json` (current) | Team-shared integrations |
| **user** | `~/.claude.json` | Personal cross-project tools |

Our project uses **project scope** for team-wide Linear and Task Master integration.

## Related Documentation

- [Claude Code MCP Documentation](https://docs.anthropic.com/claude-code/mcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Linear API Documentation](https://developers.linear.app/)
- [Task Master AI Documentation](https://www.npmjs.com/package/task-master-ai)

## Support

For issues with MCP configuration:

1. Check this documentation first
2. Review troubleshooting section
3. Check Claude Code issues: https://github.com/anthropics/claude-code/issues
4. Ask in team chat for project-specific questions
