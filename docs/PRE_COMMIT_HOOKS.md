# Pre-commit Hooks Setup

Pre-commit hooks automatically run code quality checks before each commit, ensuring code standards are maintained.

## Installation

### Prerequisites

- Python 3.7+
- Git

### Setup

1. **Install pre-commit framework**:
   ```bash
   pip install pre-commit
   ```

2. **Install hooks**:
   ```bash
   ./scripts/setup-hooks.sh
   ```

   Or manually:
   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

3. **Verify installation**:
   ```bash
   pre-commit run --all-files
   ```

## Configured Hooks

### Python Code Quality

- **Ruff Linter**: Checks Python code style (PEP 8)
- **Ruff Formatter**: Auto-formats Python code

### YAML/JSON/TOML Validation

- **YAML Checker**: Validates YAML syntax
- **JSON Checker**: Validates JSON syntax
- **TOML Checker**: Validates TOML syntax

### File Quality

- **Merge Conflict Checker**: Detects unresolved merge conflicts
- **End of File Fixer**: Ensures files end with newline
- **Trailing Whitespace**: Removes trailing whitespace
- **Private Key Detector**: Detects accidentally committed secrets

### Docker

- **Dockerfile Linter**: Checks Dockerfile best practices

### Markdown

- **Markdown Linter**: Checks Markdown formatting

### Commit Messages

- **Commitizen**: Validates commit message format (Conventional Commits)

### Security

- **Detect Secrets**: Scans for accidentally committed secrets

### TypeScript/JavaScript

- **ESLint**: Checks TypeScript/JavaScript code quality

## Usage

### Automatic Execution

Hooks run automatically before each commit:
```bash
git commit -m "Your commit message"
```

### Manual Execution

Run hooks on all files:
```bash
pre-commit run --all-files
```

Run specific hook:
```bash
pre-commit run ruff --all-files
```

### Skip Hooks

Skip all hooks (not recommended):
```bash
git commit --no-verify
```

Skip specific hook:
```bash
SKIP=ruff git commit -m "Your message"
```

## Configuration

Edit `.pre-commit-config.yaml` to customize hooks:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix]  # Auto-fix issues
```

## Common Issues

### "command not found: pre-commit"

Install pre-commit:
```bash
pip install pre-commit
```

### Hooks not running

Reinstall hooks:
```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

### "Hook failed" errors

1. Review the error message
2. Fix the issue (e.g., format code with Ruff)
3. Stage changes: `git add .`
4. Retry commit: `git commit -m "message"`

### Slow hook execution

Hooks run on changed files only. To speed up:
- Exclude large directories in `.pre-commit-config.yaml`
- Use `stages: [commit]` to run only on commit

## Best Practices

1. **Keep hooks updated**:
   ```bash
   pre-commit autoupdate
   ```

2. **Review hook output**:
   - Understand what each hook does
   - Fix issues before committing

3. **Use consistent formatting**:
   - Let Ruff auto-format code
   - Follow Conventional Commits

4. **Commit frequently**:
   - Smaller commits are easier to review
   - Hooks run faster on fewer changes

5. **Document custom hooks**:
   - Add comments to `.pre-commit-config.yaml`
   - Update this documentation

## Troubleshooting

### Hooks modifying files

Some hooks auto-fix issues (e.g., Ruff Formatter). After running:
1. Review changes: `git diff`
2. Stage changes: `git add .`
3. Retry commit: `git commit -m "message"`

### Commit message validation fails

Ensure commit message follows Conventional Commits:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Example:
```
feat(backend): Add question difficulty scoring

Implemented difficulty calculation based on:
- Question complexity
- Answer options
- Time required

Related to TF-123
```

## Related Documentation

- [Pre-commit Framework](https://pre-commit.com)
- [Ruff Documentation](https://docs.astral.sh/ruff)
- [Conventional Commits](https://www.conventionalcommits.org)
- [ESLint Documentation](https://eslint.org)
