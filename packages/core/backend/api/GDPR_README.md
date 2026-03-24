# GDPR Compliance Documentation

## Overview

ExamCraft AI implements GDPR (General Data Protection Regulation) compliance features to protect user privacy and data rights.

## Implemented GDPR Rights

### 1. Right to Data Portability (Article 20)

**Endpoint:** `GET /api/v1/gdpr/export-data`

**Description:** Allows users to export all their personal data in a structured, machine-readable format (JSON).

**Exported Data Includes:**
- User profile information (email, name, institution, roles)
- All uploaded documents
- Generated questions and exams
- Activity logs (last 1000 entries)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/gdpr/export-data" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "export_date": "2025-10-20T13:45:00Z",
    "user_profile": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "created_at": "2025-01-15T10:00:00Z",
      "institution_id": 1,
      "roles": ["dozent"]
    },
    "documents": [...],
    "questions": [...],
    "exams": [...],
    "activity_logs": [...]
  },
  "format": "JSON",
  "gdpr_article": "Article 20 - Right to Data Portability"
}
```

### 2. Right to Erasure (Article 17)

#### 2.1 Request Account Deletion (30-Day Grace Period)

**Endpoint:** `POST /api/v1/gdpr/request-deletion`

**Description:** Initiates account deletion with a 30-day grace period. User can cancel within this period.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/gdpr/request-deletion" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "message": "Account deletion scheduled",
  "deletion_date": "2025-11-19T13:45:00Z",
  "grace_period_days": 30,
  "cancellation_info": "You can cancel this request within 30 days by logging in",
  "gdpr_article": "Article 17 - Right to Erasure"
}
```

#### 2.2 Cancel Account Deletion

**Endpoint:** `POST /api/v1/gdpr/cancel-deletion`

**Description:** Cancels a pending account deletion request.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/gdpr/cancel-deletion" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "message": "Account deletion cancelled successfully"
}
```

#### 2.3 Immediate Account Deletion

**Endpoint:** `DELETE /api/v1/gdpr/delete-account-now`

**Description:** Immediately deletes the account (requires password confirmation). **This action is irreversible!**

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/gdpr/delete-account-now" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "your_password"}'
```

**Example Response:**
```json
{
  "success": true,
  "message": "Account deleted successfully",
  "gdpr_article": "Article 17 - Right to Erasure"
}
```

**What Gets Deleted:**
- User account
- All uploaded documents
- All generated questions and exams
- All sessions
- OAuth accounts

**What Gets Retained (for compliance):**
- Audit logs (anonymized after 90 days)

## Security Features

### 1. Authentication Required
All GDPR endpoints require valid JWT authentication.

### 2. Password Confirmation
Immediate account deletion requires password confirmation to prevent accidental deletion.

### 3. Audit Logging
All GDPR actions are logged for compliance:
- Data exports
- Deletion requests
- Deletion cancellations
- Account deletions

### 4. Grace Period
Account deletion has a 30-day grace period to prevent accidental data loss.

## Database Schema

### User Model Extensions

```python
class User(Base):
    # ... existing fields ...

    # GDPR Compliance
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_deletion_date = Column(DateTime(timezone=True), nullable=True)
```

## Testing

### Run GDPR Tests

```bash
# Run all GDPR tests
pytest backend/tests/test_gdpr_api.py -v

# Run specific test class
pytest backend/tests/test_gdpr_api.py::TestGDPRDataExport -v

# Run specific test
pytest backend/tests/test_gdpr_api.py::TestGDPRDataExport::test_export_user_data_success -v
```

### Test Coverage

- ✅ Data export functionality
- ✅ Account deletion request
- ✅ Deletion cancellation
- ✅ Immediate deletion
- ✅ Password verification
- ✅ Grace period validation
- ✅ Audit logging
- ✅ Data cleanup

## Frontend Integration

### Example: Data Export Button

```typescript
import { useState } from 'react';

const ExportDataButton = () => {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('examcraft_access_token');
      const response = await fetch('http://localhost:8000/api/v1/gdpr/export-data', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      // Download as JSON file
      const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `examcraft-data-export-${new Date().toISOString()}.json`;
      a.click();
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button onClick={handleExport} disabled={loading}>
      {loading ? 'Exporting...' : 'Export My Data'}
    </button>
  );
};
```

### Example: Delete Account Button

```typescript
import { useState } from 'react';

const DeleteAccountButton = () => {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!confirm('Are you sure? This action is irreversible!')) {
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('examcraft_access_token');
      const response = await fetch('http://localhost:8000/api/v1/gdpr/delete-account-now', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      });

      if (response.ok) {
        // Logout and redirect
        localStorage.clear();
        window.location.href = '/';
      } else {
        alert('Deletion failed. Please check your password.');
      }
    } catch (error) {
      console.error('Deletion failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Enter password to confirm"
      />
      <button onClick={handleDelete} disabled={loading}>
        {loading ? 'Deleting...' : 'Delete Account'}
      </button>
    </div>
  );
};
```

## Compliance Notes

### Data Retention Policy

- **User Data:** Deleted immediately upon request (or after 30-day grace period)
- **Audit Logs:** Retained for 90 days, then anonymized
- **Backups:** Deleted data is removed from backups within 30 days

### User Rights

Users have the right to:
1. ✅ Access their data (Data Export)
2. ✅ Delete their data (Account Deletion)
3. ✅ Rectify their data (Profile Update - already implemented)
4. ✅ Restrict processing (Account Suspension - already implemented)
5. ✅ Data portability (JSON Export)

### Legal Basis

- **Consent:** Users consent to data processing during registration
- **Contract:** Data processing necessary for service provision
- **Legitimate Interest:** Security and fraud prevention

## Migration

To add GDPR fields to existing database:

```bash
# Run Alembic migration
cd backend
alembic upgrade head
```

Or manually:

```sql
ALTER TABLE users ADD COLUMN deletion_requested_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN scheduled_deletion_date TIMESTAMP WITH TIME ZONE;
```

## Future Enhancements

- [ ] Automated deletion after grace period (background job)
- [ ] Email notifications for deletion requests
- [ ] Data anonymization instead of deletion (for analytics)
- [ ] GDPR consent management UI
- [ ] Cookie consent banner
- [ ] Privacy policy generator

## Support

For GDPR-related questions or data requests, contact:
- Email: privacy@examcraft.ai
- Data Protection Officer: dpo@examcraft.ai

## References

- [GDPR Official Text](https://gdpr-info.eu/)
- [Article 17 - Right to Erasure](https://gdpr-info.eu/art-17-gdpr/)
- [Article 20 - Right to Data Portability](https://gdpr-info.eu/art-20-gdpr/)
