# Audit-Attribut-Abdeckung: Design-Spezifikation

> **Ziel:** Alle vorgesehenen Audit- und Tracking-Felder in der ExamCraft-Datenbank korrekt befuellen, damit das db-query MCP-Tool aussagekraeftige Analysen liefern kann.

**Ansatz:** Punktuelle Fixes an bestehenden Endpoints und Services. Drei neue Spalten auf dem User-Modell, Befuellung bestehender leerer Felder, zusaetzlicher AuditLog-Eintrag fuer Profil-Updates. Keine neuen Abstraktionen, kein Refactoring.

---

## 1. Neue Felder auf dem User-Modell

Drei neue Spalten in `packages/core/backend/models/auth.py` auf der `User`-Klasse:

| Feld | Typ | Nullable | Default | Zweck |
|------|-----|----------|---------|-------|
| `email_verified_at` | `DateTime(timezone=True)` | YES | NULL | Zeitpunkt der Email-Verifikation |
| `password_changed_at` | `DateTime(timezone=True)` | YES | NULL | Letzte Passwort-Aenderung (inkl. initiales Setzen) |
| `registration_method` | `String(20)` | YES | NULL | `password`, `google`, `microsoft` |

Alle nullable — kein Problem mit bestehenden Daten. Erfordert eine Alembic-Migration.

---

## 2. Bestehende Felder befuellen

### 2.1 `last_login_at` + `last_login_ip` (User-Tabelle)

Diese Felder existieren bereits im Schema, werden aber nie gesetzt.

**Login-Endpoint** (`packages/core/backend/api/auth.py`, nach erfolgreicher Authentifizierung, vor `db.commit()`):
```python
user.last_login_at = func.now()
user.last_login_ip = http_request.client.host if http_request.client else None
```

**OAuth-Callback-Endpoints** (`packages/core/backend/api/auth.py`, in den Google/Microsoft Callback-Endpoints, NICHT in `oauth_service.py`):
Die `Request`-Objekt ist in `oauth_service.py` nicht verfuegbar. Stattdessen werden `last_login_at` und `last_login_ip` im Callback-Endpoint gesetzt, nachdem `find_or_create_user_from_oauth()` den User zurueckgibt.

**Hinweis: Double-Commit ist beabsichtigt.** `find_or_create_user_from_oauth()` fuehrt intern bereits `db.commit()` aus (fuer User/OAuth-Account-Erstellung). Die Login-Tracking-Felder werden in einem separaten Commit danach gesetzt. Das ist akzeptabel, da es sich um zwei logisch getrennte Operationen handelt (Account-Management vs. Login-Tracking).

```python
user = oauth_service.find_or_create_user_from_oauth(provider, user_info, token)
# Zweiter Commit fuer Login-Tracking (bewusst separat)
user.last_login_at = func.now()
user.last_login_ip = request.client.host if request.client else None
db.commit()
```

### 2.2 `oauth_id` (User-Tabelle)

Feld existiert, wird nie befuellt.

**Wichtig:** `oauth_id` hat ein `unique=True` Constraint. Ein User kann aber mehrere OAuth-Accounts haben (Google + Microsoft). Policy: `oauth_id` wird beim **ersten** OAuth-Login gesetzt und danach nicht mehr ueberschrieben. Es speichert die ID des primaeren OAuth-Providers.

**Bei OAuth-Neuregistrierung** (`oauth_service.py`, `find_or_create_user_from_oauth()`, Pfad c — neuer User, vor `db.flush()`):
```python
new_user.oauth_id = user_info["provider_user_id"]
```

**Bei bestehendem User mit OAuth-Linking** (Pfad b — User existiert, neuer OAuth-Account, vor `db.commit()`):
```python
if not existing_user.oauth_id:
    existing_user.oauth_id = user_info["provider_user_id"]
```

**Bei bestehendem OAuth-User** (Pfad a — returning login, vor `db.commit()`):
```python
if not oauth_account.user.oauth_id:
    oauth_account.user.oauth_id = oauth_account.provider_user_id
```

### 2.3 `oauth_provider` (User-Tabelle) — Pre-existing Bug Fix

Im Pfad c (neuer User, Zeile 311-321) wird `oauth_provider` NICHT gesetzt, obwohl es im Pfad b (Zeile 261) gesetzt wird. Wird mitkorrigiert:
```python
new_user.oauth_provider = provider
```

---

## 3. Neue Felder befuellen

### 3.1 `registration_method`

Wird **einmalig bei Erstellung** gesetzt und danach nicht mehr ueberschrieben (auch nicht bei spaeterem OAuth-Linking).

- **Register-Endpoint** (`auth.py`): `user.registration_method = "password"`
- **OAuth-Neuregistrierung** (`oauth_service.py`, Pfad c): `new_user.registration_method = provider` (z.B. `"google"`, `"microsoft"`)
- **OAuth-Linking** (Pfad b): Nicht setzen — User hat sich urspruenglich per Passwort registriert.

### 3.2 `email_verified_at`

- **Email-Verification-Endpoint** (`auth.py`): `user.email_verified_at = func.now()` zusammen mit `user.is_email_verified = True`
- **OAuth-Neuregistrierung** (`oauth_service.py`, Pfad c): `new_user.email_verified_at = datetime.now(timezone.utc)` (OAuth-User sind automatisch verifiziert)
- **OAuth-Linking** (Pfad b): `existing_user.email_verified_at = existing_user.email_verified_at or datetime.now(timezone.utc)` (nur setzen falls noch nicht verifiziert)

### 3.3 `password_changed_at`

- **Register-Endpoint** (`auth.py`): `user.password_changed_at = func.now()` (initiales Passwort)
- **Change-Password-Endpoint** (`auth.py`): `user.password_changed_at = func.now()`
- **Set-Password-Endpoint** (`auth.py`): `current_user.password_changed_at = func.now()` (OAuth-User setzt erstmals Passwort)

---

## 4. Fehlender AuditLog fuer Profil-Updates

**PATCH `/me` Endpoint** (`auth.py`) erfordert zwei Aenderungen:

### 4.1 `Request`-Parameter hinzufuegen

Aktuell hat der Endpoint nur `request: UserProfileUpdate`. Fuer den AuditLog brauchen wir das HTTP-Request-Objekt:

```python
@router.patch("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    request: UserProfileUpdate,
    http_request: Request,  # NEU — fuer AuditLog IP/User-Agent
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
```

### 4.2 AuditLog-Eintrag nach erfolgreichem Update

**Reihenfolge ist wichtig:** Zuerst Profil-Aenderungen committen, dann AuditLog schreiben. `AuditService.log_action()` fuehrt intern ein eigenes `db.commit()` durch. Falls der AuditLog fehlschlaegt, macht er intern ein `db.rollback()` — die Profil-Aenderungen muessen davor bereits persistiert sein.

```python
from services.audit_service import AuditService

changed_fields = list(request.model_dump(exclude_unset=True).keys())

# Existing profile field updates...
db.commit()  # Profil-Aenderungen zuerst persistieren
db.refresh(current_user)

# AuditLog nur wenn tatsaechlich Felder geaendert wurden
if changed_fields:
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

Hinweis: `AuditService.log_action()` ist eine `@staticmethod` und wird synchron aufgerufen (kein `await`). Sie erwartet `db: Session` als ersten Parameter und fuehrt intern `db.add()` + `db.commit()` aus.

---

## 5. Aenderungsuebersicht

| Datei | Aenderungen |
|-------|------------|
| `packages/core/backend/models/auth.py` | +3 neue Spalten (`email_verified_at`, `password_changed_at`, `registration_method`) |
| `packages/core/backend/api/auth.py` | Login: +`last_login_at/ip`, Register: +`registration_method/password_changed_at`, Verify: +`email_verified_at`, Change-PW: +`password_changed_at`, Set-PW: +`password_changed_at`, PATCH /me: +`http_request` Param + AuditLog, OAuth-Callbacks: +`last_login_at/ip` |
| `packages/core/backend/services/oauth_service.py` | +`oauth_id`, +`oauth_provider` (Bug-Fix Pfad c), +`registration_method`, +`email_verified_at` |
| Alembic-Migration | 1 neue Migration fuer 3 Spalten |

## 6. Nicht im Scope

- Kein Refactoring bestehender Services
- Keine neuen Abstraktionen (kein TrackingService, keine Events)
- Keine Aenderungen an bestehender Logik — nur Ergaenzungen
- Keine Backfill-Migration fuer bestehende User-Daten (Felder bleiben NULL fuer historische Eintraege)
- db-query MCP Tool Aenderungen nicht noetig (neue Felder werden automatisch erkannt)

## 7. Testbarkeit

Tests in `packages/core/backend/tests/test_audit_coverage.py`:

- **Login**: Nach erfolgreichem Login ist `user.last_login_at` != NULL und `user.last_login_ip` != NULL
- **OAuth-Login**: Nach OAuth-Callback ist `user.last_login_at` != NULL, `user.oauth_id` != NULL, `user.oauth_provider` != NULL
- **Registrierung**: `user.registration_method == "password"` und `user.password_changed_at` != NULL
- **OAuth-Registrierung**: `user.registration_method == provider` und `user.email_verified_at` != NULL
- **Email-Verifikation**: Nach Verify ist `user.email_verified_at` != NULL
- **Passwort-Aenderung**: Nach Change-PW ist `user.password_changed_at` aktualisiert
- **Set-Password**: Nach Set-PW ist `user.password_changed_at` gesetzt
- **Profil-Update**: Nach PATCH /me existiert ein AuditLog mit `action="update_user"` und `changed_fields`
- **Multi-OAuth**: Bei zweitem OAuth-Provider bleibt `user.oauth_id` unveraendert (first-write-wins)
- **Registration-Method Immutability**: Bei OAuth-Linking bleibt `user.registration_method` unveraendert
