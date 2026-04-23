# Institutions

Institutions organize users into groups — for example, a school, a university, or a department. Each user belongs to exactly one institution.

Navigate to `/admin` and select the **Institutions** tab.

## Create Institution

1. Click on **New Institution**
2. Enter the following information:

| Field | Description | Required |
|------|-------------|:-----------:|
| Name | Institution name (e.g., "Zurich Cantonal School") | ✓ |
| Description | Optional additional information | — |

3. Click on **Create Institution**

The new institution appears immediately in the list and is available for selection in user management.

## Assign Users to Institution

You can assign users to an institution in two ways:

**When creating a new user**: Select the institution directly in the creation form. See [User Management](user-mgmt.md).

**Via institution details**:

1. Click on the institution
2. Switch to the **Users** tab
3. Click on **Add User**
4. Select the user from the list

## Edit Institution

1. Click on the institution name in the institutions list
2. Customize the name or description
3. Click on **Save Changes**

## Institution-Specific Settings

Depending on your ExamCraft installation configuration, you can make the following institution-specific settings:

- **Default Subscription**: Which plan is assigned to new users of this institution by default
- **Allowed Login Methods**: Email/Password and/or Google OAuth

!!! note "Settings Depend on Your Installation"
    The available settings may vary depending on your ExamCraft version.
    Contact your IT administrator if you have questions.

## Delete Institution

!!! warning "Caution: Not Reversible"
    Deleting an institution removes the institution and all assignments.
    Users of the institution are not deleted but lose their institution assignment.
    Consider carefully whether deleting is really the right action — often just renaming the institution is enough.

1. Click on the institution
2. Click on **Delete Institution**
3. Confirm the action by entering the institution name

## Next Steps

- [:octicons-arrow-right-24: Manage Users](user-mgmt.md)
- [:octicons-arrow-right-24: Usage Overview](monitoring.md)
