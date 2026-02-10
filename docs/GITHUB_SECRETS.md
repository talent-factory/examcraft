# GitHub Secrets Configuration

This document describes how to configure GitHub Secrets for ExamCraft AI CI/CD Pipeline.

## Overview

GitHub Secrets are encrypted environment variables that are used in GitHub Actions workflows. They are essential for:
- Accessing private repositories (Submodules)
- API authentication (Claude API)
- Deployment automation (Fly.io)

## Required Secrets

### 1. FLY_API_TOKEN

**Purpose**: Authenticate with Fly.io for automated deployments

**How to Create**:
1. Install Fly CLI: `brew install flyctl` or `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create deploy token: `fly tokens create org`
4. Copy the token
5. Add to repository secrets as `FLY_API_TOKEN`

**Usage**: Used in CI/CD workflows to deploy Backend and Frontend to Fly.io

### 2. SUBMODULE_TOKEN

**Purpose**: Access private Git submodules (Premium & Enterprise packages)

**How to Create**:
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Set name: `ExamCraft Submodule Token`
4. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org data)
5. Generate and copy the token
6. Add to repository secrets as `SUBMODULE_TOKEN`

**Usage**: Used in CI/CD workflows to checkout private submodules

### 3. ANTHROPIC_API_KEY

**Purpose**: Claude API authentication for Premium feature tests

**How to Create**:
1. Go to [Anthropic Console](https://console.anthropic.com)
2. Navigate to API Keys
3. Create a new API key
4. Copy the key
5. Add to repository secrets as `ANTHROPIC_API_KEY`

**Usage**: Used in Premium package tests and question generation

## How to Add Secrets to Repository

### Via GitHub Web UI

1. Go to your repository on GitHub
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Enter Name and Value
5. Click "Add secret"

### Via GitHub CLI

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com

# Add a secret
gh secret set SECRET_NAME --body "secret_value"

# List all secrets
gh secret list

# Delete a secret
gh secret delete SECRET_NAME
```

## Security Best Practices

1. **Rotate Tokens Regularly**
   - Review and rotate tokens every 90 days
   - Immediately rotate if compromised

2. **Use Minimal Permissions**
   - Only grant necessary scopes
   - Use separate tokens for different purposes

3. **Monitor Usage**
   - Check GitHub Actions logs for secret usage
   - Review Fly.io deployment history: `fly releases -a examcraft-api`

4. **Never Commit Secrets**
   - Use `.env.example` for template
   - Add `.env` to `.gitignore`
   - Use pre-commit hooks to detect secrets

5. **Audit Access**
   - Review who has access to secrets
   - Use branch protection rules
   - Require reviews for production deployments

## Verification

To verify secrets are configured correctly:

1. **Check CI/CD Workflow**
   - Go to Actions tab
   - Run a workflow manually
   - Check logs for successful authentication

2. **Test Submodule Access**
   ```bash
   git submodule update --init --recursive
   ```

3. **Test Fly.io Token**
   ```bash
   FLY_API_TOKEN=<your-token> fly status -a examcraft-api
   ```

4. **Test API Keys**
   ```bash
   # Backend
   cd packages/core/backend
   python -c "import os; print('ANTHROPIC_API_KEY' in os.environ)"
   ```

## Troubleshooting

### "Permission denied" when accessing submodules

- Verify `SUBMODULE_TOKEN` has `repo` scope
- Check token hasn't expired
- Ensure token is added to correct repository

### "Invalid API key" errors

- Verify API key is correct and not expired
- Check API key has necessary permissions
- Ensure key is for correct service (Anthropic, Fly.io)

### Deployment not triggering

- Verify `FLY_API_TOKEN` is set correctly
- Check branch name matches trigger condition (main)
- Review GitHub Actions logs for errors
- Test manually: `make deploy`

### Fly.io authentication failed

- Create a new token: `fly tokens create org`
- Update the secret in GitHub
- Verify token has access to the org: `fly orgs list`

## Related Documentation

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub CLI Documentation](https://cli.github.com/manual)
- [Fly.io Tokens Documentation](https://fly.io/docs/flyctl/tokens-create/)
- [Anthropic API Documentation](https://docs.anthropic.com)
