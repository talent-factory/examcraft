# Roles and Permissions

ExamCraft AI uses a role-based access control system (RBAC). Each user is assigned a role that determines which features they can use.

Navigate to `/admin` and select the **Roles** tab to view the role assignments for your institution.

![Admin Roles and Permissions](../screenshots/admin/admin-roles.png)

## Available Roles

ExamCraft AI has two roles:

| Role | Description |
|------|-------------|
| **INSTRUCTOR** | Default role for teaching staff — access to all learning features |
| **ADMIN** | Extended role for institution administrators — additional access to the admin panel |

## Permissions Overview

| Feature | INSTRUCTOR | ADMIN |
|---------|:----------:|:-----:|
| Upload and manage documents | ✓ | ✓ |
| Generate AI exams | ✓ | ✓ |
| Generate RAG exams | ✓ | ✓ |
| Use Review Queue | ✓ | ✓ |
| Use Exam Composer | ✓ | ✓ |
| Use Prompt Library | ✓ | ✓ |
| Edit own profile | ✓ | ✓ |
| **User management** | — | ✓ |
| **Manage institutions** | — | ✓ |
| **View usage overview** | — | ✓ |
| **Assign roles** | — | ✓ |
| **Manage subscription and quotas** | — | ✓ |
| View submissions (`submissions:read`) | ✓ | ✓ |
| Import submissions (`submissions:import`) | ✓ | ✓ |
| Grade submissions (`submissions:grade`) | ✓ | ✓ |
| Manage students (`students:manage`) | — | ✓ |
| Configure Moodle connection (`moodle:configure`) | — | ✓ |
| Manage grading schemes (`grading_schemes:manage`) | — | ✓ (Enterprise) |

## Assigning or Changing a Role

Role assignment is done in [User Management](user-mgmt.md):

1. Navigate to `/admin` → **Users** tab
2. Open the desired user
3. Select the new value in the **Role** field (`INSTRUCTOR` or `ADMIN`)
4. Click on **Save Changes**

The new role takes effect immediately — the user will see the updated interface on their next page load.

!!! warning "Assign the ADMIN Role Sparingly"
    Only assign the ADMIN role to people who genuinely need to manage users and
    institution settings. Too many administrators increases the risk of
    unintentional configuration changes.

## Subscription Tiers and Permissions

The role (INSTRUCTOR / ADMIN) controls **who** can access which features. The [subscription tier](subscription.md) (Free, Starter, Professional, Enterprise) additionally controls **how much** a user can use — for example, the number of documents or questions that can be generated per month.

Both mechanisms operate independently: an ADMIN on the Free tier has access to the admin panel but the same usage limits as an INSTRUCTOR on the Free tier.

## Update Notice v1.4 — New Permissions

!!! warning "Automatic Assignment to Reviewer Role"
    With the v1.4 update, the Reviewer role automatically receives the `submissions:grade` permission. Anyone who wants to separate grading from pure review activity should define a custom role without this permission **before the update**.

    The `grading_schemes:manage` permission is **not** assigned automatically — it is exclusively reserved for Admin and Institution Owner roles in the Enterprise tier.

### Default Role Mapping (from v1.4)

| Role | New Permissions |
|------|----------------|
| INSTRUCTOR | `submissions:read`, `submissions:import`, `submissions:grade` |
| ADMIN | All of the above + `students:manage`, `moodle:configure` |
| Institution Owner | Additionally `grading_schemes:manage` (Enterprise) |

## Next Steps

- [:octicons-arrow-right-24: Manage Users](user-mgmt.md)
- [:octicons-arrow-right-24: Subscription and Quotas](subscription.md)
- [:octicons-arrow-right-24: Manage Institutions](institutions.md)
