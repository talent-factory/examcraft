# Organizational Units

!!! note "New Permission Required"
    Creating, moving, deleting, and viewing the full list of organizational units requires the `manage_org_units` permission, which is assigned to the ADMIN role by default. Without this permission the **Organizational Units** tab is not visible — every signed-in user only sees their own memberships, for example when choosing a team-visibility scope.

ExamCraft AI models an institution's internal structure through organizational units — **departments** with nested **teams** underneath. Navigate to `/admin` and select the **Organizational Units** tab.

## Creating an Organizational Unit

1. Navigate to `/admin` → **Organizational Units** tab
2. Click **+ Create**
3. Enter a **name** and choose the **type** (`Department` or `Team`)
4. Optionally select a **parent unit** — a team typically sits below a department
5. Optionally assign a **granted role** (see below)
6. **Save**

!!! warning "Type is fixed after creation"
    The type (`Department`/`Team`) cannot be changed after the unit has been created.

    The name must also be unique within the same level — two units with the same name and the same parent unit are not allowed.

## Moving an Organizational Unit

Open the unit via the edit icon and select a new parent in the **Parent unit** field. A unit cannot be moved beneath one of its own sub-units.

## Deleting an Organizational Unit

If an organizational unit has sub-units, deleting it permanently removes **all** nested departments/teams as well. The confirmation dialog shows the number of affected sub-units.

If documents, prompts, questions, exams, or competency frameworks with team visibility still reference the unit or one of its sub-units, deletion is rejected — remove or reassign the affected resources first.

## Granted Role and Team Visibility

The organizational structure is not purely informational — it can control two things:

- **Granted role**: if a role is assigned to an organizational unit, all **direct** members of that unit automatically receive that role's permissions — in addition to their own role. This inheritance does not cascade through sub-units.
- **Team visibility**: for documents, prompts, questions, exams, and competency frameworks set to "Team" visibility, organizational-unit membership — including the hierarchy — determines who can see them.

Assign users to organizational units via the **Org Units** button in [User Management](user-mgmt.md).

## Next Steps

- [:octicons-arrow-right-24: Roles and Permissions](roles.md)
- [:octicons-arrow-right-24: Manage Users](user-mgmt.md)
