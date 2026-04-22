# Exam Composer

The Exam Composer allows you to compile approved questions into a complete exam and export it in various formats.

!!! note "Prerequisite"
    In the Exam Composer, only questions that have been approved in the [Review Queue](review-queue.md) are available. Generate questions and review them first before you compose an exam.

## Create a New Exam

### Step 1: Open Exam Composer

Click on **Exam Composer** in the navigation or select the corresponding tile on the [Dashboard](dashboard.md). Route: `/exams/compose`.

### Step 2: Start a New Exam

Click on **Create New Exam** and fill in the following fields:

| Field | Description |
|------|-------------|
| Title | Name of the exam (e.g., "Algorithms — Semester Exam 2026") |
| Description | Optional additional information about the exam |
| Date | Planned exam date |

The title is the key element that uniquely identifies your exam. Choose a meaningful name that clearly indicates the subject, course, and time period. The description provides additional context for you and your colleagues — such as information about difficulty level, target audience, or special focus areas.

### Step 3: Select Questions

Select questions from the list of approved questions:

- Click **+ Add** next to each desired question
- Use filters to find questions by **question type**, **difficulty**, or **source document**
- The total number of selected questions is displayed at the top

!!! tip "Create Balanced Exam"
    Aim for a balanced mix: different question types (Multiple Choice and open questions), varying difficulty levels, and if possible different topics. A balanced exam promotes fair assessment and authentic understanding of content.

The filter functions help you find the right questions efficiently. Use the filter options systematically: Start with the desired question type (e.g., only Multiple Choice for quick tests or a mix of MC and open questions for comprehensive exams). Then filter by difficulty to achieve a balanced distribution. Finally, you can selectively filter by source documents if you want to focus on specific chapters or topics.

### Step 4: Set Question Order

Arrange the selected questions in the desired order using drag and drop. The questions are automatically numbered. Consider whether you want to start with easier questions to introduce examinees to the topic, or deliberately place harder questions first. The order can also be thematically meaningful — group related questions to help examinees understand connections.

### Step 5: Export Exam

Click on **Export** and choose the desired format:

| Format | Description |
|--------|-------------|
| Markdown (.md) | Text-based format, ideal for further editing or publishing. Optionally include answer solutions. |
| JSON (.json) | Machine-readable format for further processing, integration with external systems, or data analysis |
| Moodle XML (.xml) | Directly importable format for the Moodle learning management system |

!!! tip "Include Solutions"
    When exporting in Markdown format, you can optionally include the solutions. Enable the **Include solutions** checkbox in the export dialog — useful for creating answer sheets or internal review.

The Markdown format is suitable for further editing or integration into documentation systems. The JSON format is ideal for technical integration — for example, when importing exam data into a custom system or performing automated evaluations. The Moodle XML format enables direct import into Moodle without manual post-processing.

## Manage Existing Exams

All created exams appear in the overview list. There you can:

- **Open**: Edit and supplement the exam
- **Duplicate**: Use as a basis for a new, similar exam
- **Export**: Export again in any format
- **Delete**: Remove the exam (not reversible)

The overview list shows important metadata such as creation date, number of questions, and last modified timestamp. Use the duplicate function to quickly create similar exams — for example, for different classes of the same year or for a makeup exam. This function saves time when composing similar exams and minimizes errors.

!!! warning "Deleted Exams"
    Deleting an exam only removes the exam composition, not the individual questions. The questions remain in the Review Queue and can be reused for future exams.

## Next Steps

- [:octicons-arrow-right-24: Generate More Questions](exam-create.md)
- [:octicons-arrow-right-24: RAG Exam from Documents](rag-exam.md)
- [:octicons-arrow-right-24: Review Queue — Review Questions](review-queue.md)
- [:octicons-arrow-right-24: Best Practices](best-practices.md)
