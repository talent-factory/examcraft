# Commit Changes

Erstellt einen Git Commit mit **Conventional Commits** Format und **Emojis**.

## Commit Message Format

```
[emoji] type(scope): description

[optional body]

[optional footer]
```

## Emoji Mapping

- ✨ `feat` - Neue Features
- 🐛 `fix` - Bug Fixes
- 📝 `docs` - Dokumentation
- 💄 `style` - Code-Formatierung
- ♻️ `refactor` - Code-Refactoring
- ⚡ `perf` - Performance-Verbesserungen
- ✅ `test` - Tests hinzufügen/ändern
- 🔧 `chore` - Build/Config-Änderungen
- 🚀 `ci` - CI/CD-Änderungen
- 🔥 `revert` - Revert eines Commits

## Verwendung

```text
/commit
```

## Workflow

1. **Staged Changes prüfen**: `git status`
2. **Commit Type bestimmen**: feat, fix, docs, etc.
3. **Emoji auswählen**: Basierend auf Type
4. **Scope identifizieren**: z.B. TF-187, backend, frontend
5. **Description schreiben**: Kurze Zusammenfassung
6. **Body erstellen**: Detaillierte Änderungen (optional)
7. **Footer hinzufügen**: Breaking Changes, Issues (optional)
8. **Pre-Commit Hooks ausführen**: Automatisch
9. **Commit erstellen**: Mit korrektem Format

## Beispiele

### Feature Commit

```
✨ feat(TF-187): Implement email verification system with Resend

Backend Implementation:
- Add EmailVerificationToken model with 24h expiration
- Add email_service.py with Resend API integration
- Implement send_verification_email() and send_welcome_email()

Frontend Implementation:
- Add VerifyEmailPage with auto-redirect after 2s
- Add EmailVerificationBanner for unverified users

Testing:
- Email verification flow tested end-to-end
```

### Bug Fix Commit

```
🐛 fix(TF-187): Prevent duplicate personal institution creation

- Check if personal institution slug already exists
- Reuse existing institution instead of creating duplicate
- Fix IntegrityError on repeated registrations
```

### Documentation Commit

```
📝 docs(README): Update deployment instructions

- Add Resend configuration steps
- Update environment variables section
- Add troubleshooting guide
```

## Pre-Commit Hooks

Der Command führt automatisch folgende Checks aus:

1. **Ruff Linter** - Python Code Quality
2. **Ruff Formatter** - Python Code Formatting
3. **YAML/JSON Validation** - Config Files
4. **End of File Fixer** - Newlines
5. **Trailing Whitespace** - Cleanup
6. **Detect Secrets** - Security Check

## Fehlerbehandlung

Wenn Pre-Commit Hooks fehlschlagen:

1. **Review Changes**: `git diff`
2. **Stage Fixes**: `git add .`
3. **Retry Commit**: Command erneut ausführen

## Commitizen Integration

Der Command verwendet die Commitizen-Konfiguration aus `pyproject.toml`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "1.1.0"
tag_format = "v$version"
message_template = "{{change_type}}{{scope}}: {{message}}"
```

## Best Practices

1. **Atomic Commits** - Ein Commit = Eine logische Änderung
2. **Descriptive Messages** - Klar und präzise
3. **Use Emojis** - Visuell erkennbare Commit-Types
4. **Reference Issues** - Linear/GitHub Issue IDs im Scope
5. **Test Before Commit** - Alle Tests müssen grün sein
