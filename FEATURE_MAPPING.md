# ExamCraft AI - Feature Mapping für Monorepo-Migration

**Erstellt:** 2025-10-21  
**Zweck:** Detaillierte Zuordnung aller Features zu Core, Premium und Enterprise Packages  
**Status:** Migration Plan für TF-151

---

## 📦 Package-Übersicht

### 🌍 Core Package (Open Source - MIT License)
- **Zielgruppe:** Community, Hobby-Projekte, Universitäten
- **Tier:** Free (5 Docs, 20 Questions/Monat, 1 User)
- **Repository:** packages/core/ (im Main Repo)

### 🌟 Premium Package (Closed Source - Proprietary)
- **Zielgruppe:** Zahlende Kunden (Starter & Professional Tier)
- **Tier:** Starter (€19/Monat), Professional (€49/Monat)
- **Repository:** packages/premium/ (Private Submodule)

### 🏢 Enterprise Package (Closed Source - Proprietary)
- **Zielgruppe:** Große Organisationen, Compliance-kritisch
- **Tier:** Enterprise (€149/Monat)
- **Repository:** packages/enterprise/ (Private Submodule)

---

## 🗂️ Backend Feature-Mapping

### ✅ CORE PACKAGE (packages/core/backend/)

#### API Endpoints

**Authentication** (auth.py)
- ✅ POST /api/auth/register - User Registration
- ✅ POST /api/auth/login - Login
- ✅ POST /api/auth/logout - Logout
- ✅ POST /api/auth/refresh - Refresh Token
- ✅ GET /api/auth/me - Get Profile
- ✅ PUT /api/auth/profile - Update Profile
- ✅ POST /api/auth/change-password - Change Password
- ✅ POST /api/auth/forgot-password - Password Reset Request
- ✅ POST /api/auth/reset-password - Reset Password

**Documents** (documents.py)
- ✅ POST /api/v1/documents/ - Upload (max 5)
- ✅ GET /api/v1/documents/ - List Documents
- ✅ GET /api/v1/documents/{id} - Get Details
- ✅ DELETE /api/v1/documents/{id} - Delete
- ✅ POST /api/v1/documents/{id}/process - Process (Basic)

**Question Generation** (rag_exams.py - Basic)
- ✅ POST /api/v1/rag/exams - Generate (Basic, ohne RAG)
- ✅ GET /api/v1/rag/exams/{id} - Get Exam
- ✅ GET /api/v1/rag/exams - List Exams

**Review** (question_review.py)
- ✅ GET /api/v1/review/queue - Review Queue
- ✅ POST /api/v1/review/{id}/approve - Approve
- ✅ POST /api/v1/review/{id}/reject - Reject
- ✅ PUT /api/v1/review/{id} - Edit Question

**Admin** (admin.py)
- ✅ GET /api/v1/admin/users - List Users
- ✅ GET /api/v1/admin/users/{id} - Get User
- ✅ PUT /api/v1/admin/users/{id} - Update User
- ✅ DELETE /api/v1/admin/users/{id} - Delete User
- ✅ POST /api/v1/admin/users/{id}/roles - Assign Roles

**GDPR** (gdpr.py)
- ✅ GET /api/v1/gdpr/export-data - Export Data
- ✅ POST /api/v1/gdpr/request-deletion - Request Deletion
- ✅ POST /api/v1/gdpr/delete-account - Delete Account

**RBAC** (v1/rbac.py)
- ✅ GET /api/v1/rbac/roles - List Roles
- ✅ POST /api/v1/rbac/roles - Create Role
- ✅ PUT /api/v1/rbac/roles/{id} - Update Role
- ✅ GET /api/v1/rbac/features - List Features
- ✅ GET /api/v1/rbac/permissions - Check Permissions

#### Services
- ✅ auth_service.py - JWT Authentication
- ✅ document_service.py - Document Management
- ✅ docling_service.py - Document Processing
- ✅ claude_service.py - Basic Question Generation
- ✅ review_service.py - Review Workflow
- ✅ rbac_service.py - RBAC Logic
- ✅ audit_service.py - Audit Logging
- ✅ redis_service.py - Session Management

#### Models
- ✅ auth.py - User, Role, Institution
- ✅ document.py - Document, DocumentChunk
- ✅ question_review.py - ReviewQueue
- ✅ rbac.py - Feature, RBACRole, SubscriptionTier

---

### �� PREMIUM PACKAGE (packages/premium/backend/)

#### API Endpoints

**RAG Generation** (rag.py - NEU)
- 🌟 POST /api/v1/rag/generate - RAG Question Generation
- 🌟 POST /api/v1/rag/search - Semantic Search

**ChatBot** (chat.py - MIGRIERT)
- 🌟 POST /api/v1/chat/sessions - Create Session
- 🌟 GET /api/v1/chat/sessions - List Sessions
- 🌟 POST /api/v1/chat/message - Send Message
- 🌟 DELETE /api/v1/chat/sessions/{id} - Delete
- 🌟 POST /api/v1/chat/sessions/{id}/to-document - Export
- 🌟 GET /api/v1/chat/sessions/{id}/download - Download

**Prompts** (prompts.py - MIGRIERT)
- 🌟 GET /api/v1/prompts - List Prompts
- 🌟 POST /api/v1/prompts - Create Prompt
- 🌟 GET /api/v1/prompts/{id} - Get Prompt
- 🌟 PUT /api/v1/prompts/{id} - Update Prompt
- 🌟 DELETE /api/v1/prompts/{id} - Delete Prompt
- 🌟 POST /api/v1/prompts/search - Semantic Search
- 🌟 POST /api/v1/prompts/{id}/render - Render Template

**Vector Search** (vector_search.py - MIGRIERT)
- 🌟 POST /api/v1/vector/search - Semantic Search
- 🌟 GET /api/v1/vector/collections - List Collections

#### Services
- 🌟 rag_service.py - RAG Generation
- 🌟 chatbot_service.py - ChatBot Logic
- 🌟 chat_export_service.py - Chat Export
- 🌟 prompt_service.py - Prompt Management
- 🌟 prompt_vector_service.py - Prompt Search
- 🌟 vector_service.py - ChromaDB
- 🌟 qdrant_vector_service.py - Qdrant
- 🌟 vector_service_factory.py - Vector Service Selection

#### Models
- 🌟 chat.py - ChatSession, ChatMessage
- 🌟 prompt.py - Prompt, PromptVersion
- 🌟 vector.py - VectorCollection

---

### 🏢 ENTERPRISE PACKAGE (packages/enterprise/backend/)

#### API Endpoints

**SSO** (sso.py - NEU)
- 🏢 POST /api/v1/sso/configure - Configure SSO
- 🏢 GET /api/v1/sso/metadata - SAML Metadata
- 🏢 POST /api/v1/sso/login - SSO Login

**Branding** (branding.py - NEU)
- 🏢 GET /api/v1/branding - Get Config
- 🏢 PUT /api/v1/branding - Update Config
- �� POST /api/v1/branding/logo - Upload Logo

**API Access** (api_access.py - NEU)
- 🏢 GET /api/v1/api-keys - List Keys
- 🏢 POST /api/v1/api-keys - Create Key
- 🏢 DELETE /api/v1/api-keys/{id} - Revoke Key

**Analytics** (analytics.py - NEU)
- 🏢 GET /api/v1/analytics/usage - Usage Stats
- 🏢 GET /api/v1/analytics/users - User Activity
- 🏢 POST /api/v1/analytics/export - Export to BI

**OAuth** (MIGRIERT von auth.py)
- 🏢 GET /api/auth/oauth/{provider}/login - OAuth Login
- 🏢 GET /api/auth/oauth/{provider}/callback - OAuth Callback

#### Services
- 🏢 sso_service.py - SSO/SAML Logic
- 🏢 oauth_service.py - OAuth (MIGRIERT)
- 🏢 branding_service.py - Branding Logic
- 🏢 api_key_service.py - API Key Management
- 🏢 analytics_service.py - Analytics
- 🏢 ldap_service.py - LDAP Integration

#### Models
- 🏢 sso.py - SSOProvider, SSOConfig
- 🏢 branding.py - BrandingConfig
- 🏢 api_key.py - APIKey, APIKeyUsage
- 🏢 analytics.py - AnalyticsEvent

---

## 🎨 Frontend Feature-Mapping

### ✅ CORE (packages/core/frontend/)

#### Pages
- ✅ Dashboard.tsx
- ✅ Documents.tsx
- ✅ Exams.tsx
- ✅ Review.tsx
- ✅ Admin.tsx

#### Components
- ✅ auth/LoginForm.tsx
- ✅ auth/RegisterForm.tsx
- ✅ DocumentUpload.tsx
- ✅ DocumentLibrary.tsx
- ✅ QuestionEditor.tsx
- ✅ ReviewQueue.tsx
- ✅ admin/UserList.tsx
- ✅ admin/RoleList.tsx
- ✅ layout/Navigation.tsx

#### Services
- ✅ AuthService.ts
- ✅ DocumentService.ts
- ✅ ExamService.ts
- ✅ ReviewService.ts
- ✅ AdminService.ts
- ✅ RBACService.ts

---

### 🌟 PREMIUM (packages/premium/frontend/)

#### Components
- 🌟 DocumentChat/ChatInterface.tsx
- 🌟 prompts/PromptLibrary.tsx
- 🌟 prompts/PromptEditor.tsx
- 🌟 RAGExamCreator.tsx

#### Services
- 🌟 ChatService.ts
- 🌟 RAGService.ts
- 🌟 promptsApi.ts

---

### 🏢 ENTERPRISE (packages/enterprise/frontend/)

#### Components
- 🏢 SSOConfig/SSOProviderList.tsx
- 🏢 CustomBranding/BrandingEditor.tsx
- 🏢 APIManagement/APIKeyList.tsx
- 🏢 AnalyticsDashboard/UsageCharts.tsx
- 🏢 auth/OAuthButtons.tsx (MIGRIERT)

---

## 📊 Migration-Statistik

### Backend
- **Core:** 12 API Files, 15 Services, 6 Models
- **Premium:** 4 API Files, 9 Services, 3 Models
- **Enterprise:** 5 API Files, 6 Services, 4 Models

### Frontend
- **Core:** 5 Pages, 25 Components, 6 Services
- **Premium:** 10 Components, 3 Services
- **Enterprise:** 15 Components

---

## 🚀 Migration-Plan

1. Backend: backend/ → packages/core/backend/
2. Premium Features → packages/premium/backend/
3. Enterprise Features → packages/enterprise/backend/
4. Frontend: frontend/ → packages/core/frontend/
5. Premium Components → packages/premium/frontend/
6. Enterprise Components → packages/enterprise/frontend/
7. Import-Pfade anpassen
8. Docker Compose Orchestration

**Status:** ✅ Feature-Mapping abgeschlossen  
**Nächster Schritt:** Backend Migration starten
