# Review Queue

The Review Queue is the central place for manual review and approval of AI-generated questions. Only after approval in the Review Queue are questions available in the [Exam Composer](exam-composer.md).

!!! note "Why a Review Queue?"
    AI-generated questions are a starting point, not the final product. The Review Queue gives you control over the quality of your exams — you decide which questions are good enough.

<!-- screenshot: review-queue-overview.png -->

## Status Overview

Each question has one of four possible statuses:

| Status | Color | Meaning |
|--------|-------|---------|
| Pending | Orange | Newly generated, not yet reviewed |
| In Review | Blue | Currently being reviewed |
| Approved | Green | Released for the Exam Composer |
| Rejected | Red | Not usable, archived |

## Filter and Search Questions

Use the filter options to keep the queue manageable:

- **Status**: Pending / In Review / Approved / Rejected
- **Difficulty**: Easy / Medium / Hard
- **Question Type**: Multiple Choice / Open Question
- **Time Period**: Filter by generation date

## Review a Question — Step by Step

### Step 1: Open Question

Click on a question with "Pending" status in the list view. The question automatically changes to "In Review" status.

<!-- screenshot: review-queue-detail.png -->

### Step 2: Review Content

In the detail view, you see:

| Field | Description |
|------|-------------|
| Question Text | The actual exam question |
| Question Type | Multiple Choice or open question |
| Difficulty | Easy / Medium / Hard |
| Answer Options | For Multiple Choice: all options including correct answer |
| Explanation | Rationale for the correct answer |
| Source Reference | Text passage from the source document |
| Confidence Score | AI's confidence estimate (0–1) |

Pay special attention to:
- Is the question text clear and unambiguous?
- Is the correct answer actually correct?
- Is the explanation understandable and educational?
- Does the stated source match the question content?

### Step 3: Decide

**Approve Question**: Click **Approve**. The question changes to "Approved" and is immediately available in the Exam Composer.

**Reject Question**: Click **Reject**. The question is archived and cannot be used. Optionally, you can provide a rejection reason.

!!! tip "When to Reject?"
    Reject questions if: the question text is unclear or ambiguous, the correct answer is wrong, the question doesn't fit the topic, or multiple answer options could be correct.

## Detail View of Individual Questions

Each question has its own URL: `/questions/review/:id`

You can share this URL to point colleagues to a specific question.

## Next Steps

Approved questions are immediately available in the [Exam Composer](exam-composer.md). From there, you can compile a complete exam and export it.

- [:octicons-arrow-right-24: Compose Exam](exam-composer.md)
- [:octicons-arrow-right-24: Generate More Questions](exam-create.md)
- [:octicons-arrow-right-24: Best Practices](best-practices.md)
