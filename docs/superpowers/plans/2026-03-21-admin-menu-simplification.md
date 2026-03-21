# Admin Menu Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the expandable Admin sidebar submenu with a single link, consolidating all admin functions as RBAC-controlled tabs in the Admin panel.

**Architecture:** Remove children from the Admin navigation item, expand Admin.tsx from 3 to 5 tabs with role-based visibility, remove redundant routes from AppWithAuth.tsx.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, RBAC via AuthContext

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `packages/core/frontend/src/hooks/useRoleBasedNavigation.ts` | Modify (lines 66-100) | Remove Admin children, add requiredRoles |
| `packages/core/frontend/src/pages/Admin.tsx` | Modify (full rewrite) | 5 RBAC-controlled tabs with data-driven rendering |
| `packages/core/frontend/src/AppWithAuth.tsx` | Modify (lines 20-21, 220-242) | Remove sub-routes and unused imports |
| `packages/core/frontend/src/components/layout/__tests__/Sidebar.test.tsx` | Modify (lines 26-36) | Update mock to remove Admin children |

---

### Task 1: Simplify Admin navigation item

**Files:**
- Modify: `packages/core/frontend/src/hooks/useRoleBasedNavigation.ts:66-100`

- [ ] **Step 1: Replace the Admin entry (lines 66-100)**

Replace the Admin object with children array with a flat entry:

```ts
    {
      label: 'Admin',
      path: '/admin',
      icon: '⚙️',
      requiredRoles: [UserRole.ADMIN],
    },
```

This removes the entire `children` array. The `requiredRoles` check is already handled by `filterNavigationItems` (line 119-122), which also grants access to superusers.

- [ ] **Step 2: Verify the app compiles**

Run: `cd packages/core/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/hooks/useRoleBasedNavigation.ts
git commit -m "refactor(admin): remove sidebar submenu, use single Admin link"
```

---

### Task 2: Expand Admin panel to 5 RBAC-controlled tabs

**Files:**
- Modify: `packages/core/frontend/src/pages/Admin.tsx` (full rewrite)

- [ ] **Step 1: Rewrite Admin.tsx with 5 data-driven tabs**

Replace the entire file content with:

```tsx
/**
 * Admin Page
 * Admin panel with RBAC-controlled tabs
 */

import React, { useState } from 'react';
import { UserManagementPage } from '../components/admin/UserManagementPage';
import { InstitutionManagementPage } from '../components/admin/InstitutionManagementPage';
import RoleManagementPage from '../components/admin/RoleManagementPage';
import SubscriptionTierOverview from '../components/admin/SubscriptionTierOverview';
import { useAuth } from '../contexts/AuthContext';
import { UserRole } from '../types/auth';

type AdminTab = 'users' | 'institutions' | 'roles' | 'audit' | 'subscription';

interface TabConfig {
  key: AdminTab;
  label: string;
  visible: boolean;
}

export const Admin: React.FC = () => {
  const { user, hasRole } = useAuth();
  const isSuperuser = user?.is_superuser ?? false;
  const isAdmin = isSuperuser || hasRole(UserRole.ADMIN);

  const tabs: TabConfig[] = [
    { key: 'users', label: 'Benutzer-Verwaltung', visible: true },
    { key: 'institutions', label: 'Institutionen', visible: isSuperuser },
    { key: 'roles', label: 'Rollen & Berechtigungen', visible: isSuperuser },
    { key: 'audit', label: 'Audit Logs', visible: isAdmin },
    { key: 'subscription', label: 'Abonnement', visible: isAdmin },
  ].filter((t): t is TabConfig => t.visible);

  const [activeTab, setActiveTab] = useState<AdminTab>(tabs[0]?.key ?? 'users');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Admin-Panel</h1>
        <p className="text-gray-600 mt-2">
          Verwalte Benutzer, Einstellungen und Systemkonfiguration
        </p>
      </div>

      <div className="flex gap-4 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="card p-6">
        {activeTab === 'users' && <UserManagementPage />}
        {activeTab === 'institutions' && <InstitutionManagementPage />}
        {activeTab === 'roles' && <RoleManagementPage />}
        {activeTab === 'audit' && (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">Audit Logs — Demnachst verfugbar</p>
          </div>
        )}
        {activeTab === 'subscription' && <SubscriptionTierOverview />}
      </div>
    </div>
  );
};
```

Key changes:
- Added `SubscriptionTierOverview` import (default export)
- Added `UserRole` import for `hasRole` check
- Derived `isAdmin` from `hasRole(UserRole.ADMIN)` (superusers already pass via `isSuperuser`)
- Tab rendering is data-driven via `tabs` array with `.filter()`
- Tab content uses single wrapper `div.card` instead of per-tab wrappers
- Audit Logs tab renders inline placeholder

- [ ] **Step 2: Verify the app compiles**

Run: `cd packages/core/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/pages/Admin.tsx
git commit -m "feat(admin): expand to 5 RBAC-controlled tabs with data-driven rendering"
```

---

### Task 3: Remove redundant routes and imports from AppWithAuth

**Files:**
- Modify: `packages/core/frontend/src/AppWithAuth.tsx:20-21` (imports)
- Modify: `packages/core/frontend/src/AppWithAuth.tsx:220-242` (routes)

- [ ] **Step 1: Remove unused imports (lines 20-21)**

Remove these two lines:

```ts
import { UserManagementPage } from './components/admin/UserManagementPage';
import RoleManagementPage from './components/admin/RoleManagementPage';
```

These components are now only used inside `Admin.tsx`.

- [ ] **Step 2: Remove the `/admin/users` and `/admin/roles` routes (lines 220-242)**

Remove the entire block:

```tsx
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <UserManagementPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin/roles"
                element={
                  <ProtectedRoute>
                    <RoleGuard allowedRoles={[UserRole.ADMIN]} requireSuperuser>
                      <AppLayout>
                        <RoleManagementPage />
                      </AppLayout>
                    </RoleGuard>
                  </ProtectedRoute>
                }
              />
```

Direct URL access to `/admin/users` or `/admin/roles` will redirect to `/dashboard` via the wildcard route.

- [ ] **Step 3: Check if `UserRole` and `RoleGuard` imports are still used**

`UserRole` is still used by the `/prompts` route (line 189). Keep it.
`RoleGuard` is still used by the `/prompts` route (line 189). Keep it.

No further import cleanup needed.

- [ ] **Step 4: Verify the app compiles**

Run: `cd packages/core/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add packages/core/frontend/src/AppWithAuth.tsx
git commit -m "refactor(admin): remove redundant /admin/users and /admin/roles routes"
```

---

### Task 4: Update Sidebar test mock

**Files:**
- Modify: `packages/core/frontend/src/components/layout/__tests__/Sidebar.test.tsx:26-36`

- [ ] **Step 1: Update the mock navigation items**

Replace the Admin entry with children (lines 26-36):

```ts
      {
        label: 'Admin',
        path: '/admin',
        icon: '⚙️',
        children: [
          {
            label: 'Users',
            path: '/admin/users',
            icon: '👥',
          },
        ],
      },
```

With a flat entry:

```ts
      {
        label: 'Admin',
        path: '/admin',
        icon: '⚙️',
      },
```

- [ ] **Step 2: Remove the submenu expansion test (lines 67-79)**

Delete the entire test block `it('expands and collapses submenu items', ...)` (lines 67-79). This test clicks an expand button that only renders when an item has `children`. Since Admin no longer has children, the expand button will not exist and the test will fail.

- [ ] **Step 3: Run the Sidebar tests**

Run: `cd packages/core/frontend && npx jest --testPathPattern="Sidebar" --no-coverage 2>&1 | tail -20`
Expected: All 5 remaining tests pass (renders sidebar, renders icons, applies active state, hides labels, renders correct href).

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/components/layout/__tests__/Sidebar.test.tsx
git commit -m "test(sidebar): update mock to reflect simplified Admin navigation"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full frontend test suite**

Run: `cd packages/core/frontend && npx jest --no-coverage 2>&1 | tail -30`
Expected: All tests pass

- [ ] **Step 2: Verify app compiles cleanly**

Run: `cd packages/core/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Final commit if any fixes were needed**

Only if previous steps required adjustments.
