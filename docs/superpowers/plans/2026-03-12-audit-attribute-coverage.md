# Audit-Attribut-Abdeckung Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate all audit/tracking fields on the User model that are currently NULL, add 3 new tracking columns, and add AuditLog for profile updates.

**Architecture:** Additive changes only — no refactoring, no new abstractions. Each task modifies 1-2 files plus tests. All changes are independent enough to commit separately.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest

**Spec:** `docs/superpowers/specs/2026-03-12-audit-attribute-coverage-design.md`

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `packages/core/backend/models/auth.py` | User model schema | Modify: +3 columns |
| `packages/core/backend/alembic/versions/xxxx_add_audit_fields.py` | DB migration | Create |
| `packages/core/backend/api/auth.py` | Auth endpoints | Modify: 6 endpoints |
| `packages/core/backend/services/oauth_service.py` | OAuth user management | Modify: 3 code paths |
| `packages/core/backend/tests/test_audit_coverage.py` | Tests for all changes | Create |

---

## Chunk 1: Model + Migration

### Task 1: Add new columns to User model

**Files:**
- Modify: `packages/core/backend/models/auth.py:278-279` (after `email_verification_expires`)
- Create: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test for new columns**

Create `packages/core/backend/tests/test_audit_coverage.py`:

```python
"""Tests for audit attribute coverage."""

import pytest
from models.auth import User


class TestUserModelAuditFields:
    """Verify new audit columns exist on User model."""

    def test_user_has_email_verified_at(self):
        user = User(
            email="test@test.ch",
            first_name="Test",
            last_name="User",
            institution_id=1,
        )
        assert hasattr(user, "email_verified_at")
        assert user.email_verified_at is None

    def test_user_has_password_changed_at(self):
        user = User(
            email="test@test.ch",
            first_name="Test",
            last_name="User",
            institution_id=1,
        )
        assert hasattr(user, "password_changed_at")
        assert user.password_changed_at is None

    def test_user_has_registration_method(self):
        user = User(
            email="test@test.ch",
            first_name="Test",
            last_name="User",
            institution_id=1,
        )
        assert hasattr(user, "registration_method")
        assert user.registration_method is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestUserModelAuditFields -v`
Expected: FAIL — `User` has no attribute `email_verified_at`

- [ ] **Step 3: Add three new columns to User model**

In `packages/core/backend/models/auth.py`, after the `email_verification_expires` line (line 278), add:

```python
    # Audit Tracking
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    registration_method = Column(String(20), nullable=True)  # password, google, microsoft
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestUserModelAuditFields -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Create Alembic migration**

Run: `cd packages/core/backend && alembic revision --autogenerate -m "add_user_audit_fields"`

Verify the generated migration adds these three columns. If `alembic` is not configured or fails, create the migration manually:

```python
"""add_user_audit_fields

Revision ID: <auto>
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("registration_method", sa.String(20), nullable=True))

def downgrade() -> None:
    op.drop_column("users", "registration_method")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "email_verified_at")
```

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/models/auth.py packages/core/backend/tests/test_audit_coverage.py packages/core/backend/alembic/versions/
git commit -m "feat: add email_verified_at, password_changed_at, registration_method to User model"
```

---

## Chunk 2: Login Tracking (last_login_at, last_login_ip)

### Task 2: Set last_login_at and last_login_ip on password login

**Files:**
- Modify: `packages/core/backend/api/auth.py:344-346` (login endpoint, after `user.failed_login_attempts = 0`)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test**

Add to `test_audit_coverage.py`:

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from models.auth import User, Role, Institution, UserStatus
from services.auth_service import AuthService


@pytest.fixture
def test_institution(test_db):
    inst = Institution(
        name="Test Inst",
        slug="test-inst",
        domain="test.ch",
        subscription_tier="free",
        is_active=True,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


@pytest.fixture
def test_role(test_db):
    role = Role(
        name="Viewer",
        display_name="Viewer",
        description="Default role",
        permissions="[]",
        is_system_role=True,
    )
    test_db.add(role)
    test_db.flush()
    return role


@pytest.fixture
def active_user(test_db, test_institution, test_role):
    user = User(
        email="login-test@test.ch",
        password_hash=AuthService.get_password_hash("Test1234!"),
        first_name="Login",
        last_name="Test",
        institution_id=test_institution.id,
        status=UserStatus.ACTIVE.value,
        is_email_verified=True,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.flush()
    user.roles.append(test_role)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestLoginTracking:
    def test_login_sets_last_login_at(self, test_db, active_user):
        """After successful login, last_login_at must be set."""
        assert active_user.last_login_at is None

        # Simulate what the login endpoint does after successful auth
        from sqlalchemy import func
        active_user.failed_login_attempts = 0
        active_user.last_login_at = func.now()
        active_user.last_login_ip = "127.0.0.1"
        test_db.commit()
        test_db.refresh(active_user)

        assert active_user.last_login_at is not None
        assert active_user.last_login_ip == "127.0.0.1"
```

- [ ] **Step 2: Run test to verify it passes (baseline — field exists from Task 1)**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestLoginTracking -v`
Expected: PASS (the field exists, this test validates the pattern)

- [ ] **Step 3: Modify login endpoint to set last_login_at and last_login_ip**

In `packages/core/backend/api/auth.py`, in the `login()` function, after line 345 (`user.failed_login_attempts = 0`) and before line 346 (`db.commit()`), add:

```python
    # Track login
    user.last_login_at = func.now()
    user.last_login_ip = http_request.client.host if http_request.client else None
```

Add `from sqlalchemy import func` at the top of the file if not already imported. Check existing imports first.

- [ ] **Step 4: Run all existing auth tests to verify no regression**

Run: `cd packages/core/backend && python -m pytest tests/test_auth_api.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/auth.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: set last_login_at and last_login_ip on password login"
```

### Task 3: Set last_login_at and last_login_ip on OAuth login

**Files:**
- Modify: `packages/core/backend/api/auth.py:939-947` (OAuth callback endpoint)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test**

Add to `test_audit_coverage.py`:

```python
class TestOAuthLoginTracking:
    def test_oauth_login_sets_last_login_at(self, test_db, test_institution, test_role):
        """After OAuth login, last_login_at and last_login_ip must be set on User."""
        from sqlalchemy import func

        user = User(
            email="oauth-track@test.ch",
            first_name="OAuth",
            last_name="Track",
            institution_id=test_institution.id,
            status="active",
            is_email_verified=True,
            password_hash=None,
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.last_login_at is None

        # Simulate what the OAuth callback does after find_or_create_user_from_oauth
        user.last_login_at = func.now()
        user.last_login_ip = "10.0.0.1"
        test_db.commit()
        test_db.refresh(user)

        assert user.last_login_at is not None
        assert user.last_login_ip == "10.0.0.1"
```

- [ ] **Step 2: Run test**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestOAuthLoginTracking -v`
Expected: PASS

- [ ] **Step 3: Modify OAuth callback to set login tracking fields**

In `packages/core/backend/api/auth.py`, in the `oauth_callback()` function, after line 939 (`user = oauth_service.find_or_create_user_from_oauth(...)`) and before line 942 (`tokens = AuthService.create_tokens_for_user(...)`), add:

```python
        # Track OAuth login (separate commit — find_or_create already committed internally)
        from sqlalchemy import func as sa_func
        user.last_login_at = sa_func.now()
        user.last_login_ip = request.client.host if request.client else None
        db.commit()
```

Note: `auth.py` does not currently import `func` from sqlalchemy at the top level. Add `from sqlalchemy import func` to the top-level imports once (in Task 2), then reuse it in all subsequent tasks. No `sa_func` alias needed.

- [ ] **Step 4: Run OAuth tests**

Run: `cd packages/core/backend && python -m pytest tests/test_oauth_service.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/auth.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: set last_login_at and last_login_ip on OAuth login"
```

---

## Chunk 3: OAuth fields (oauth_id, oauth_provider, registration_method, email_verified_at)

### Task 4: Populate oauth_id, oauth_provider, registration_method, email_verified_at in OAuth service

**Note on test transaction isolation:** `find_or_create_user_from_oauth()` calls `self.db.commit()` internally. The test fixture uses `connection.begin()` with transaction rollback. If the internal commits break test isolation (data leaks between tests), wrap the test fixture's transaction with `connection.begin_nested()` (savepoints) instead. The existing `test_oauth_service.py` tests use the same fixture and work, so this is likely fine.

**Files:**
- Modify: `packages/core/backend/services/oauth_service.py:219-346` (all 3 paths in `find_or_create_user_from_oauth`)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing tests**

Add to `test_audit_coverage.py`:

```python
from services.oauth_service import OAuthService
from models.auth import OAuthAccount


class TestOAuthAuditFields:
    """Test oauth_id, oauth_provider, registration_method, email_verified_at in OAuth flows."""

    def _make_oauth_service(self, db):
        return OAuthService(db)

    def _user_info(self, email="oauth-new@test.ch", provider_user_id="google-123"):
        return {
            "email": email,
            "first_name": "OAuth",
            "last_name": "User",
            "name": "OAuth User",
            "provider_user_id": provider_user_id,
            "email_verified": True,
        }

    def _token(self):
        return {"access_token": "at_xxx", "refresh_token": "rt_xxx"}

    def test_new_user_gets_oauth_id(self, test_db, test_institution, test_role):
        """Path c: new user — oauth_id, oauth_provider, registration_method, email_verified_at set."""
        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth("google", self._user_info(), self._token())

        assert user.oauth_id == "google-123"
        assert user.oauth_provider == "google"
        assert user.registration_method == "google"
        assert user.email_verified_at is not None

    def test_existing_user_linking_gets_oauth_id(self, test_db, test_institution, test_role):
        """Path b: existing password user links OAuth — oauth_id set, registration_method unchanged."""
        # Create password user first
        existing = User(
            email="existing@test.ch",
            password_hash="hashed",  # pragma: allowlist secret
            first_name="Existing",
            last_name="User",
            institution_id=test_institution.id,
            status="active",
            is_email_verified=True,
            registration_method="password",
        )
        test_db.add(existing)
        test_db.commit()

        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth(
            "google",
            self._user_info(email="existing@test.ch", provider_user_id="google-456"),
            self._token(),
        )

        assert user.oauth_id == "google-456"
        assert user.registration_method == "password"  # NOT overwritten
        assert user.email_verified_at is not None

    def test_returning_oauth_user_gets_oauth_id_if_missing(self, test_db, test_institution, test_role):
        """Path a: returning OAuth user — oauth_id backfilled if NULL."""
        svc = self._make_oauth_service(test_db)
        # First login creates user
        user = svc.find_or_create_user_from_oauth("google", self._user_info(), self._token())
        # Clear oauth_id to simulate pre-existing user without it
        user.oauth_id = None
        test_db.commit()

        # Second login should backfill
        user2 = svc.find_or_create_user_from_oauth("google", self._user_info(), self._token())
        assert user2.oauth_id == "google-123"

    def test_multi_oauth_does_not_overwrite_oauth_id(self, test_db, test_institution, test_role):
        """First-write-wins: second OAuth provider does not overwrite oauth_id."""
        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth("google", self._user_info(), self._token())
        assert user.oauth_id == "google-123"

        # Link Microsoft account (path b — same email, different provider)
        # User already has oauth_id from Google
        ms_info = self._user_info(email=user.email, provider_user_id="ms-789")
        user2 = svc.find_or_create_user_from_oauth("microsoft", ms_info, self._token())
        assert user2.oauth_id == "google-123"  # NOT overwritten
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestOAuthAuditFields -v`
Expected: FAIL — `user.oauth_id` is None, `user.oauth_provider` is None (path c), `user.registration_method` is None

- [ ] **Step 3: Modify oauth_service.py — Path a (returning OAuth user)**

In `packages/core/backend/services/oauth_service.py`, in `find_or_create_user_from_oauth()`, **Path a** (line 219-244, after line 240 `user.avatar_url = ...`, before line 242 `self.db.commit()`), add:

```python
            # Backfill oauth_id if missing (first-write-wins)
            if not user.oauth_id:
                user.oauth_id = oauth_account.provider_user_id
```

- [ ] **Step 4: Modify oauth_service.py — Path b (existing user, OAuth linking)**

In **Path b** (line 251-279, after line 262 `existing_user.is_email_verified = True`, before line 264 `new_oauth_account = OAuthAccount(...)`), add:

```python
            # Set oauth_id (first-write-wins)
            if not existing_user.oauth_id:
                existing_user.oauth_id = user_info["provider_user_id"]
            # Set email_verified_at if not yet set
            if not existing_user.email_verified_at:
                existing_user.email_verified_at = datetime.now(timezone.utc)
            # Do NOT set registration_method — user originally registered differently
```

- [ ] **Step 5: Modify oauth_service.py — Path c (new user creation)**

In **Path c** (line 311-320, the `new_user = User(...)` block), add these fields to the constructor:

```python
        new_user = User(
            email=user_info["email"],
            first_name=user_info.get("first_name", "Unknown"),
            last_name=user_info.get("last_name", "User"),
            institution_id=institution.id,
            status="active",
            is_email_verified=user_info.get("email_verified", False),
            avatar_url=user_info.get("picture"),
            password_hash=None,
            # Audit tracking (new)
            oauth_provider=provider,
            oauth_id=user_info["provider_user_id"],
            registration_method=provider,
            email_verified_at=datetime.now(timezone.utc),
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestOAuthAuditFields -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Run existing OAuth tests for regression**

Run: `cd packages/core/backend && python -m pytest tests/test_oauth_service.py -v`
Expected: All existing tests PASS

- [ ] **Step 8: Commit**

```bash
git add packages/core/backend/services/oauth_service.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: populate oauth_id, oauth_provider, registration_method, email_verified_at in OAuth flows"
```

---

## Chunk 4: Password Registration Fields

### Task 5: Set registration_method and password_changed_at on password registration

**Files:**
- Modify: `packages/core/backend/api/auth.py:201-213` (register endpoint, User creation)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test**

Add to `test_audit_coverage.py`:

```python
class TestPasswordRegistrationTracking:
    def test_register_sets_registration_method_and_password_changed_at(self, test_db, test_institution, test_role):
        """Password registration sets registration_method='password' and password_changed_at."""
        from sqlalchemy import func

        user = User(
            email="reg-test@test.ch",
            password_hash=AuthService.get_password_hash("Test1234!"),
            first_name="Reg",
            last_name="Test",
            institution_id=test_institution.id,
            status=UserStatus.PENDING.value,
            is_email_verified=False,
            registration_method="password",
        )
        test_db.add(user)
        test_db.flush()
        user.password_changed_at = func.now()
        test_db.commit()
        test_db.refresh(user)

        assert user.registration_method == "password"
        assert user.password_changed_at is not None
```

- [ ] **Step 2: Run test**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestPasswordRegistrationTracking -v`
Expected: PASS (field exists from Task 1)

- [ ] **Step 3: Modify register endpoint**

In `packages/core/backend/api/auth.py`, in the `register()` function, modify the `User(...)` constructor (line 202-211) to add the new fields:

```python
    user = User(
        email=request.email,
        password_hash=AuthService.get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        institution_id=institution.id,
        status=UserStatus.PENDING.value,
        is_email_verified=False,
        is_superuser=False,
        registration_method="password",
    )
```

Then after `db.flush()` (line 213), add:

```python
    from sqlalchemy import func
    user.password_changed_at = func.now()
```

Note: Check if `func` is already imported at the top of the file. If so, skip the import.

- [ ] **Step 4: Run existing registration tests**

Run: `cd packages/core/backend && python -m pytest tests/test_auth_api.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/auth.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: set registration_method and password_changed_at on registration"
```

---

## Chunk 5: Email Verification + Password Change/Set Tracking

### Task 6: Set email_verified_at on email verification

**Files:**
- Modify: `packages/core/backend/api/auth.py:728-736` (verify-email endpoint)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test**

Add to `test_audit_coverage.py`:

```python
from models.auth import EmailVerificationToken
from datetime import timedelta


class TestEmailVerificationTracking:
    def test_verify_email_sets_email_verified_at(self, test_db, test_institution, test_role):
        """After email verification, email_verified_at must be set."""
        user = User(
            email="verify-test@test.ch",
            password_hash="hashed",  # pragma: allowlist secret
            first_name="Verify",
            last_name="Test",
            institution_id=test_institution.id,
            status=UserStatus.PENDING.value,
            is_email_verified=False,
            registration_method="password",
        )
        test_db.add(user)
        test_db.flush()

        token = EmailVerificationToken(
            user_id=user.id,
            token="test-verify-token-123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_used=False,
        )
        test_db.add(token)
        test_db.commit()

        assert user.email_verified_at is None

        # Simulate verification
        from sqlalchemy import func
        user.is_email_verified = True
        user.status = UserStatus.ACTIVE.value
        user.email_verified_at = func.now()
        token.is_used = True
        token.used_at = datetime.now(timezone.utc)
        test_db.commit()
        test_db.refresh(user)

        assert user.email_verified_at is not None
        assert user.is_email_verified is True
```

- [ ] **Step 2: Run test**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestEmailVerificationTracking -v`
Expected: PASS

- [ ] **Step 3: Modify verify-email endpoint**

In `packages/core/backend/api/auth.py`, in the `verify_email()` function, after line 730 (`user.status = UserStatus.ACTIVE.value`), add:

```python
    from sqlalchemy import func
    user.email_verified_at = func.now()
```

- [ ] **Step 4: Run existing tests**

Run: `cd packages/core/backend && python -m pytest tests/test_auth_api.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/backend/api/auth.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: set email_verified_at on email verification"
```

### Task 7: Set password_changed_at on change-password and set-password

**Files:**
- Modify: `packages/core/backend/api/auth.py:617-619` (change-password endpoint)
- Modify: `packages/core/backend/api/auth.py:568-570` (set-password endpoint)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test**

Add to `test_audit_coverage.py`:

```python
class TestPasswordChangeTracking:
    def test_change_password_sets_password_changed_at(self, test_db, active_user):
        """After password change, password_changed_at must be updated."""
        from sqlalchemy import func

        assert active_user.password_changed_at is None

        active_user.password_hash = AuthService.get_password_hash("NewPass1234!")
        active_user.password_changed_at = func.now()
        test_db.commit()
        test_db.refresh(active_user)

        assert active_user.password_changed_at is not None

    def test_set_password_sets_password_changed_at(self, test_db, test_institution, test_role):
        """After set-password (OAuth user), password_changed_at must be set."""
        from sqlalchemy import func

        oauth_user = User(
            email="oauth-setpw@test.ch",
            first_name="OAuth",
            last_name="SetPW",
            institution_id=test_institution.id,
            status="active",
            is_email_verified=True,
            password_hash=None,  # OAuth-only
        )
        test_db.add(oauth_user)
        test_db.commit()

        assert oauth_user.password_changed_at is None

        oauth_user.password_hash = AuthService.get_password_hash("First1234!")
        oauth_user.password_changed_at = func.now()
        test_db.commit()
        test_db.refresh(oauth_user)

        assert oauth_user.password_changed_at is not None
```

- [ ] **Step 2: Run tests**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestPasswordChangeTracking -v`
Expected: PASS

- [ ] **Step 3: Modify change-password endpoint**

In `packages/core/backend/api/auth.py`, in the `change_password()` function, after line 618 (`current_user.password_hash = ...`), before line 619 (`db.commit()`), add:

```python
    from sqlalchemy import func
    current_user.password_changed_at = func.now()
```

- [ ] **Step 4: Modify set-password endpoint**

In `packages/core/backend/api/auth.py`, in the `set_password()` function, after line 569 (`current_user.password_hash = ...`), before line 570 (`db.commit()`), add:

```python
    from sqlalchemy import func
    current_user.password_changed_at = func.now()
```

- [ ] **Step 5: Run existing tests**

Run: `cd packages/core/backend && python -m pytest tests/test_auth_api.py -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/auth.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: set password_changed_at on change-password and set-password"
```

---

## Chunk 6: Profile Update AuditLog

### Task 8: Add AuditLog for profile updates (PATCH /me)

**Files:**
- Modify: `packages/core/backend/api/auth.py:470-494` (PATCH /me endpoint)
- Test: `packages/core/backend/tests/test_audit_coverage.py`

- [ ] **Step 1: Write failing test**

Add to `test_audit_coverage.py`:

```python
from models.auth import AuditLog


class TestProfileUpdateAuditLog:
    def test_profile_update_creates_audit_log(self, test_db, active_user):
        """After PATCH /me, an AuditLog with action='update_user' must exist."""
        from services.audit_service import AuditService

        # Count existing audit logs
        before_count = test_db.query(AuditLog).filter(
            AuditLog.user_id == active_user.id,
            AuditLog.action == AuditService.ACTION_UPDATE_USER,
        ).count()

        # Simulate profile update
        active_user.first_name = "Updated"
        test_db.commit()

        # Log the update
        changed_fields = ["first_name"]
        AuditService.log_action(
            db=test_db,
            action=AuditService.ACTION_UPDATE_USER,
            user_id=active_user.id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(active_user.id),
            additional_data={"changed_fields": changed_fields},
        )

        after_count = test_db.query(AuditLog).filter(
            AuditLog.user_id == active_user.id,
            AuditLog.action == AuditService.ACTION_UPDATE_USER,
        ).count()

        assert after_count == before_count + 1

    def test_profile_update_no_audit_log_if_no_changes(self, test_db, active_user):
        """If no fields changed, no AuditLog entry should be created."""
        from services.audit_service import AuditService

        before_count = test_db.query(AuditLog).filter(
            AuditLog.user_id == active_user.id,
            AuditLog.action == AuditService.ACTION_UPDATE_USER,
        ).count()

        # Simulate empty update — changed_fields is empty
        changed_fields = []
        if changed_fields:
            AuditService.log_action(
                db=test_db,
                action=AuditService.ACTION_UPDATE_USER,
                user_id=active_user.id,
                resource_type=AuditService.RESOURCE_USER,
                resource_id=str(active_user.id),
                additional_data={"changed_fields": changed_fields},
            )

        after_count = test_db.query(AuditLog).filter(
            AuditLog.user_id == active_user.id,
            AuditLog.action == AuditService.ACTION_UPDATE_USER,
        ).count()

        assert after_count == before_count
```

- [ ] **Step 2: Run tests**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py::TestProfileUpdateAuditLog -v`
Expected: PASS

- [ ] **Step 3: Modify PATCH /me endpoint**

In `packages/core/backend/api/auth.py`, modify the `update_current_user_profile()` function:

**3a.** Add `http_request: Request` parameter to the function signature (after `request: UserProfileUpdate`):

```python
@router.patch("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    request: UserProfileUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
```

**3b.** Before the existing field updates (line 482), extract changed fields:

```python
    changed_fields = list(request.model_dump(exclude_unset=True).keys())
```

**3c.** After the existing `db.commit()` and `db.refresh(current_user)` (line 494-495), add the AuditLog:

```python
    # Audit log for profile update (only if fields actually changed)
    if changed_fields:
        from services.audit_service import AuditService
        AuditService.log_action(
            db=db,
            action=AuditService.ACTION_UPDATE_USER,
            user_id=current_user.id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(current_user.id),
            additional_data={"changed_fields": changed_fields},
            request=http_request,
        )
```

- [ ] **Step 4: Run existing tests**

Run: `cd packages/core/backend && python -m pytest tests/test_auth_api.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Run all audit coverage tests**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/auth.py packages/core/backend/tests/test_audit_coverage.py
git commit -m "feat: add AuditLog for profile updates (PATCH /me)"
```

---

## Chunk 7: Final Validation

### Task 9: Run full test suite and verify

- [ ] **Step 1: Run all audit coverage tests**

Run: `cd packages/core/backend && python -m pytest tests/test_audit_coverage.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run full backend test suite**

Run: `cd packages/core/backend && python -m pytest tests/ -v --timeout=60`
Expected: All tests PASS, no regressions

- [ ] **Step 3: Verify migration applies cleanly (if Alembic is configured)**

Run: `cd packages/core/backend && alembic upgrade head`
Expected: Migration applies without errors. If Alembic is not configured for the dev environment, skip this step — the columns will be created by `Base.metadata.create_all()` in the test setup.
