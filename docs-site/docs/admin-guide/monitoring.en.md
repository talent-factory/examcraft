# Usage Overview

The usage overview in the Admin Panel gives you an overview of the activities and resource consumption of your institution.

Navigate to `/admin` and select the **Usage** tab.

## Available Metrics

| Metric | Description |
|--------|-------------|
| Active Users | Number of users with at least one activity in the selected time period |
| Generated Questions | Total number of AI-generated questions |
| Validated Questions | Number of questions approved in the Review Queue |
| Uploaded Documents | Number and total size of processed documents |
| API Calls | Number of Claude API requests (relevant for cost control) |

## Select Time Period

Filter the display by time period:

- **Today** — Activities of the current day
- **This Week** — Current week (Monday to today)
- **This Month** — Current calendar month
- **Custom** — Select your own time period via date picker

## Usage per User

In the detail view, you see the breakdown by users:

| Column | Description |
|--------|-------------|
| User | Name and email |
| Generated Questions | Number in selected time period |
| Documents | Number of uploaded documents |
| Last Activity | Date of last action |

Click on a table row to view details for a specific user.

## Monitor Subscription Quotas

Pay special attention to quota usage:

!!! warning "Pay Attention to Quota Limits"
    For Free and Starter subscriptions, there are monthly limits for questions and documents. If users regularly reach the limits, you should consider upgrading. See [Subscription](../user-guide/subscription.md).

## Note: Technical Infrastructure Monitoring

The usage overview in the Admin Panel shows **application metrics** (who uses what). For **technical infrastructure monitoring** (server load, logs, error rate), contact your IT administrator or DevOps manager — this information is not part of the Admin Panel.

## Frequently Asked Questions about Usage Overview

**How often are the numbers updated?**

The metrics are updated in real-time. After each action (question generation, document upload, review), the metrics are updated within a few seconds.

**Can I export the data?**

Currently, there is no direct data export from the Admin Panel. However, you can take a screenshot of the usage overview or manually document the numbers. CSV/PDF export is planned for future releases.

**What does "API Calls" mean?**

Each AI question generation counts as one or more API calls to the Claude API. For example, if you generate 10 questions, it can be 1–3 API calls (depending on batch size). This information is relevant for cost control on Professional and Enterprise plans, as you need to manage your API budget.

**Do API calls differ between AI and RAG exams?**

RAG exams may require more API calls because the AI first performs the semantic search and then generates the questions. AI exams are usually faster. The exact difference is measured in the API call metric.

**Can I see users with high consumption?**

Yes! In the "Usage per User" detail view, you can see which users have generated how many questions and how many documents they use. This helps identify power users and plan resources.

## Next Steps

- [:octicons-arrow-right-24: Manage Users](user-mgmt.md)
- [:octicons-arrow-right-24: Manage Institutions](institutions.md)
