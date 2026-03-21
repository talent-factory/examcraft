# Admin Menu Vereinfachung

## Ziel

Das Admin-Submenu in der Sidebar (5 expandierbare Sub-Items) wird durch einen einzelnen "Admin"-Link ersetzt. Alle Admin-Funktionen werden als RBAC-gesteuerte Tabs innerhalb des Admin-Panels dargestellt.

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `packages/core/frontend/src/hooks/useRoleBasedNavigation.ts` | Admin `children` entfernen, `requiredRoles: [UserRole.ADMIN]` setzen |
| `packages/core/frontend/src/pages/Admin.tsx` | 5 Tabs datengetrieben mit RBAC, neue Tabs Audit Logs (Platzhalter) und Subscription |
| `packages/core/frontend/src/AppWithAuth.tsx` | Separate Routes `/admin/users` und `/admin/roles` entfernen, Imports aufräumen |

## Design

### 1. Sidebar-Navigation (`useRoleBasedNavigation.ts`)

Der Admin-Eintrag wird von einem Eltern-Element mit `children`-Array zu einem einfachen Link:

```ts
{
  label: 'Admin',
  path: '/admin',
  icon: '⚙️',
  requiredRoles: [UserRole.ADMIN],
}
```

Die feingranulare RBAC-Steuerung (Superuser vs. Admin) passiert auf Tab-Ebene innerhalb des Admin-Panels.

### 2. Admin-Panel (`Admin.tsx`)

5 Tabs mit rollenbasierter Sichtbarkeit:

```ts
type AdminTab = 'users' | 'institutions' | 'roles' | 'audit' | 'subscription';

const tabs = [
  { key: 'users', label: 'Benutzer-Verwaltung', visible: true },
  { key: 'institutions', label: 'Institutionen', visible: isSuperuser },
  { key: 'roles', label: 'Rollen & Berechtigungen', visible: isSuperuser },
  { key: 'audit', label: 'Audit Logs', visible: isAdmin },
  { key: 'subscription', label: 'Abonnement', visible: isAdmin },
].filter(t => t.visible);
```

RBAC-Logik:
- `isAdmin` = User hat Admin-Rolle (Audit Logs, Subscription)
- `isSuperuser` = `user.is_superuser` (Institutions, Roles)
- Users-Tab ist fuer alle Admins sichtbar

Tab-Inhalte:
- `users`: bestehende `UserManagementPage`
- `institutions`: bestehende `InstitutionManagementPage`
- `roles`: bestehende `RoleManagementPage`
- `subscription`: bestehende `SubscriptionTierOverview`
- `audit`: Platzhalter-Komponente

### 3. Routing (`AppWithAuth.tsx`)

Entfernt werden:
- Route `/admin/users` mit `UserManagementPage`
- Route `/admin/roles` mit `RoleManagementPage` und `RoleGuard`

Die Route `/admin` bleibt bestehen. Keine neuen Routen noetig.

Direkte URL-Zugriffe auf `/admin/users` oder `/admin/roles` werden durch die Wildcard-Route auf `/dashboard` umgeleitet. Dies ist akzeptabel, da diese URLs nicht extern verlinkt sind.

### 4. Nicht betroffen

- Sidebar-Komponente (`Sidebar.tsx`): Rendert Items bereits korrekt mit und ohne Children, keine Aenderung noetig.
- Backend-APIs: Keine Aenderungen.
- Bestehende Admin-Komponenten: Werden 1:1 wiederverwendet.
