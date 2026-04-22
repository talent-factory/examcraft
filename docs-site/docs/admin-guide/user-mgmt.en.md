# User Management

As an administrator, you manage all users of your institution through the Admin Panel. Navigate to `/admin` and select the **Users** tab.

## Create User

1. Click on **New User**
2. Fill out the form:

| Field | Description | Required |
|------|-------------|:-----------:|
| First and Last Name | Full name of the person | ✓ |
| Email Address | Used as login name | ✓ |
| Role | ADMIN or INSTRUCTOR (see below) | ✓ |
| Institution | Assignment to institution | ✓ |
| Temporary Password | First password (user can change it) | ✓ |

3. Click on **Create User**
4. The new user receives a welcome email with login credentials

!!! tip "Recommend Google OAuth"
    Recommend new users to switch to Google OAuth at first login. This simplifies password management and increases security.

## User Roles

ExamCraft AI has two roles:

| Role | Permissions |
|-------|---------------|
| **INSTRUCTOR** | Upload documents, generate questions, Review Queue, Exam Composer, Prompt Library |
| **ADMIN** | All INSTRUCTOR permissions + user management, institutions, Admin Panel |

Assign the ADMIN role only to people who actually need to manage users.

## Edit User

1. Click on the user's name in the user list
2. Customize the desired fields (name, email, role, institution)
3. Click on **Save Changes**

## Reset Password (as Admin)

1. Open the user in management
2. Click on **Reset Password**
3. A new temporary password is generated and sent to the user by email
4. The user is prompted to change the password at the next login

## Disable User

When a user leaves the institution or no longer needs access:

1. Open the user
2. Click on **Disable User**
3. Confirm the action

!!! warning "Disable Instead of Delete"
    Disable users instead of deleting them. This way, all created questions and
    exams are retained and can be attributed. A disabled user can no longer log
    in, but their data is retained.

## Assign User to Institution

You can change the institution assignment at any time:

1. Open the user
2. Select the new institution in the **Institution** field
3. Save the change

More information about institutions: [Manage Institutions](institutions.md)

## Next Steps

- [:octicons-arrow-right-24: Manage Institutions](institutions.md)
- [:octicons-arrow-right-24: Usage Overview](monitoring.md)
