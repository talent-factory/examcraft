# Profile and Account Settings

On the profile page, you can customize your personal information and change your password. All changes are saved immediately and visible throughout the application.

## Open Profile

Click on your name or avatar in the top right and select **Profile** from the dropdown menu. Alternatively, navigate directly to `/profile`.

The profile page is divided into several sections: Personal Information, Security, and Account Overview.

## Change Personal Information

The **Personal Information** section contains all basic information about your account.

### Customize Name

1. Click the edit icon next to your name in the **Personal Information** section
2. Enter the new name
3. Click **Save**

The change takes effect immediately and is displayed in the navigation and in all generated documents. Your name will also be visible to other administrators when working with them in your workspace.

### Change Email Address

1. Click the edit icon next to your email address
2. Enter the new email address
3. Click **Save**
4. You will immediately receive a confirmation email at the new address
5. Click the link in the email to confirm the change

Until you click the confirmation link, the new email address is not fully activated. Your old email address remains valid until you confirm the new one.

!!! warning "Email with Google OAuth"
    If you sign in via Google OAuth, your email address is managed by Google.
    You cannot change it directly in ExamCraft AI. Change it instead in your
    Google Account at [https://myaccount.google.com](https://myaccount.google.com).

!!! warning "Email with Microsoft OAuth"
    Similarly, email addresses for Microsoft OAuth logins are managed by Microsoft. Changes must be made in your Microsoft Account.

## Change Password

In the **Security** section, you can change your password at any time. This is recommended if you suspect your password has been compromised.

### Update Password

1. Click **Change Password** in the **Security** section
2. Enter your current password
3. Enter the new password
4. The new password must meet the following requirements:
    - At least 8 characters long
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one number (0-9)
5. Repeat the new password for confirmation
6. Click **Save Password**

After the change, you must sign in with your new password at the next login. All active sessions in other browsers or devices are automatically terminated.

!!! note "Password with Google OAuth"
    When signing in via Google OAuth, there is no password option in ExamCraft AI.
    Your password is fully managed via your Google Account. You can change it in
    [Google Account Settings](https://myaccount.google.com).

!!! note "Password with Microsoft OAuth"
    Similarly, the password for Microsoft OAuth logins is managed via your Microsoft Account.

## Account Overview

In the **Account** section, you see a summary of your account details:

| Information | Description |
|-------------|-------------|
| Role | Your user role (ADMIN or INSTRUCTOR) — determines your permissions |
| Institution | The institution to which you are assigned |
| Subscription | Your current subscription plan and limits |
| Member Since | Date and time of account creation |

This information is read-only and can only be changed by an administrator for your account. If you need to change your role, institution, or subscription plan, contact your administrator.

### Understanding Your Role

Your role determines which features you can use:

- **ADMIN** – Full access to all features, user management, institutional settings
- **INSTRUCTOR** – Access to question generation, prompt management, RAG exams

### Institution

Your institution is assigned by your administrator. All your documents and exams are assigned to this institution.

## Security Best Practices

To keep your account secure, follow these recommendations:

1. **Use a strong password** – Use at least 8 characters with uppercase and lowercase letters, numbers, and special characters
2. **Change password regularly** – Change your password at least every 90 days
3. **Secure connection** – Use ExamCraft AI only over secure HTTPS connections
4. **Logout after use** – Sign out when using someone else's computer
5. **Two-Factor Authentication** – If available, enable additional security measures

## Next Steps

- [:octicons-arrow-right-24: Manage Subscription](subscription.md)
- [:octicons-arrow-right-24: Go to Dashboard](dashboard.md)
- [:octicons-arrow-right-24: Generate Questions](exam-create.md)
