# Prompt Library

The Prompt Library enables management of reusable AI prompts for question generation. Instead of entering the same prompt manually each time, save proven prompts centrally and use them directly when creating exams.

!!! note "Access"
    The Prompt Library is available to users with **ADMIN** and **INSTRUCTOR** roles.
    Route: `/prompts`

## Overview

- **Versioning** – All changes are tracked
- **Rollback** – Go back to earlier versions
- **Semantic Search** – Find prompts by meaning
- **Analytics** – Monitor performance and costs
- **Template System** – Reusable prompts with variables
- **Web Interface** – No code changes needed

## Prompt View

The Prompt Library displays all available prompts in a grid layout with:

- Prompt name and description
- Category (System / User / Template)
- Use case, version, and status
- Tags and usage counter

### Actions

You can manage each prompt with the following actions:

- **Edit** – Open prompt in editor
- **Versions** – Show version history
- **Delete** – Remove prompt

## Create New Prompt

1. Click on **New Prompt**
2. Fill in the following fields:

| Field | Description |
|---|-------|
| Name | Unique identifier (e.g., `system_prompt_question_generation`) |
| Description | Brief explanation of purpose |
| Category | System Prompt / User Prompt / Few-Shot Example / Template |
| Use Case | Purpose of use (e.g., `question_generation`) |
| Content | Prompt text (Markdown supported) |
| Tags | Keywords for easier search |
| Active | Activate immediately? |

3. Click on **Save**

The new prompt is immediately available in the library and can be used when generating questions.

## Template Variables

Use template variables to create dynamic prompts that automatically adapt to your inputs.

### Syntax

Use curly braces: `{variable_name}`

Example:
```
Generate {count} questions on the topic {topic} at difficulty level {difficulty}
```

### Available Variables for RAG Exams

The following variables are automatically available:

- `topic` – Exam topic
- `difficulty` – Difficulty level (easy, medium, hard)
- `language` – Language of the questions
- `context` – Automatically extracted document content

These variables are automatically replaced with your inputs or document data at runtime.

## Version Control

The Prompt Library automatically manages all versions of your prompts.

### Version Management

- Automatic version numbers (v1, v2, v3...)
- Only one version can be active at a time
- Old versions are retained (unlimited)

### Revert to Earlier Version

1. Open the prompt and click on **Versions**
2. Select the desired version from the list
3. Click on **Activate**
4. Confirm the rollback

The older version is then active again for new question generations.

## Usage Analytics

Monitor the performance of your prompts with detailed metrics:

| Metric | Description |
|----|-------|
| Uses | Number of calls since creation |
| Success Rate | % of successful generations |
| Average Latency | Average response time in seconds |
| Total Tokens | Total token consumption |

These metrics help you evaluate and optimize the efficiency of your prompts.

## Semantic Search

Find prompts by meaning, not just by keywords.

### Perform Semantic Search

1. Switch to the **Semantic Search** tab
2. Enter a search query (e.g., "generate multiple choice questions")
3. Filter if needed by:
    - **Category** – Narrow down prompt type
    - **Use Case** – Select specific use case
    - **Similarity Threshold** – Set minimum relevance
4. Results are automatically sorted by relevance

Semantic search understands the meaning of your query and finds prompts even if they don't match textually.

## Use Prompt in Question Generation

1. Open [Create Exam](exam-create.md) or [Create RAG Exam](rag-exam.md)
2. In the **Prompt Configuration** section, click on **Choose from Library**
3. Select the desired prompt from the list
4. Template variables are automatically populated with your inputs
5. Click on **Generate**

!!! tip "Premium: Prompt Upload"
    Starting with the **Professional subscription**, you can upload your own prompt files and import them into the library. See [Subscription](subscription.md).

## Next Steps

- [:octicons-arrow-right-24: Generate Questions](exam-create.md)
- [:octicons-arrow-right-24: Create RAG Exam](rag-exam.md)
- [:octicons-arrow-right-24: Manage Subscription](subscription.md)
