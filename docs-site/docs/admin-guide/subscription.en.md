# Subscription Tiers and Quotas

ExamCraft AI offers four subscription tiers with different features and quotas:

| Tier | Documents | Generated Questions/Month | RAG | AI Models | Support |
|------|-----------|--------------------------|-----|-----------|---------|
| **Free** | 5 | 20 | No | GPT-4 Mini | Community |
| **Starter** | 50 | 100 | Yes (limited) | GPT-4 Mini | Email |
| **Professional** | Unlimited | Unlimited | Yes | GPT-4 + Claude 3 | Email + Priority |
| **Enterprise** | Unlimited | Unlimited | Yes | All models | Dedicated Support |

## Tier Details

### Free Tier

**Ideal for**: Individual educators and small tests

- **Document management**: Maximum 5 documents at a time
- **Question generation**: Up to 20 questions per month
- **Question types**: Multiple choice and open questions
- **Features**:
  - AI exams (simple prompts)
  - Review Queue (manual review)
  - Basic user profiles
- **No RAG**: Questions are only generated for the entered topic, not from documents
- **Support**: Community forum

### Starter Tier

**Ideal for**: Courses with regular exams

- **Document management**: Maximum 50 documents at a time
- **Question generation**: Up to 100 questions per month
- **RAG exams**: Create from documents (up to 5 per request)
- **Features**:
  - AI exams with extended prompt templates
  - RAG-based exams with source references
  - Confidence scores for quality control
  - Review Queue with extended filter options
- **Prompt templates**: 10 predefined prompt templates
- **Support**: Email support (48h response time)

### Professional Tier

**Ideal for**: Institutions with multiple courses

- **Document management**: Unlimited number and size
- **Question generation**: Unlimited questions per month
- **RAG exams**: With up to 50 documents per request
- **Features**:
  - All Starter features
  - Extended prompt templates (50+)
  - Custom prompt creation
  - Admin dashboard with detailed usage analysis
  - Multiple administrators per institution
  - User role management (educator, admin)
- **API access**: Limited (100 requests/day)
- **Support**: Email + priority queue (24h response time)
- **Backup & security**: Automatic daily backups

### Enterprise Tier

**Ideal for**: Large organisations and enterprises

- **All Professional features** plus:
- **Document management**: Unlimited number, size, and concurrent processing
- **Question generation**: Unlimited questions and requests per month
- **RAG exams**: Unlimited documents per request, extended indexing
- **Features**:
  - Custom AI models and fine-tuning
  - Extended security configuration (SSO, LDAP)
  - White-label options
  - Bulk import and export of documents
  - Unlimited API access
  - Audit logs for compliance
- **Support**: Dedicated account manager, 24/7 hotline
- **Infrastructure**: Optional self-hosted solution, own Qdrant instance
- **SLA**: 99.9% availability guaranteed
- **Training**: Free onboarding session and training

## Quotas and Limits

The following table shows technical limits per tier:

| Limit | Free | Starter | Professional | Enterprise |
|-------|------|---------|-------------|-----------|
| Concurrent uploads | 1 | 5 | 10 | Unlimited |
| Max. document size | 10 MB | 50 MB | 100 MB | Unlimited |
| Batch question generation | 1 | 3 | 10 | Unlimited |
| API calls/month | 50 | 500 | 5000 | Unlimited |
| Retention period (data) | 3 months | 6 months | 12 months | Custom |

## Upgrade and Downgrade

- **Upgrades**: Effective immediately, proportional billing
- **Downgrades**: At the end of the current billing period
- **Quota enforcement**: Requests are blocked when quotas are exceeded

## Next Steps

- [:octicons-arrow-right-24: Manage Users and Their Tiers](user-mgmt.md)
- [:octicons-arrow-right-24: View Usage Statistics](monitoring.md)
