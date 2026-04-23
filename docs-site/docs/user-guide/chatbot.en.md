# Document ChatBot

The ChatBot enables interactive conversations with your uploaded documents.

!!! warning "Premium Feature"
    Document Chat is available starting with the **Starter subscription** and requires
    the `document_chatbot` permission. This feature is not accessible with the Free subscription.
    See [Subscription](subscription.md).

## Select Document

1. Click **Document ChatBot** in the navigation
2. Select a document from the dropdown menu
3. The ChatBot loads the context (2–5 seconds)

## Start Chat

Ask questions about your document:

- "Explain the Heapsort algorithm to me"
- "What are the differences between Quicksort and Mergesort?"
- "Summarize Chapter 3"

!!! tip "Tips for Good Questions"
    - Specific and clearly formulated
    - Related to document content
    - Use follow-up questions for deeper understanding

## Understand Answers

Each answer contains:

- **Main Text** – AI-generated answer
- **Sources** – Relevant text passages from the document
- **Confidence** – Reliability (0–1)

| Confidence | Meaning |
|-----------|---------|
| > 0.8 | Very reliable |
| 0.6–0.8 | Reliable |
| < 0.6 | Use with caution |

## Chat History

- All messages are saved within the session
- Context is retained (multi-turn)
- Select another document to start a new conversation

## Limitations

- **Only uploaded documents** as knowledge source — no internet access
- **No access** to content not uploaded as document
- **Session-bound** — conversation history is not saved between sessions
- Start a new conversation by selecting another document

## Example Prompts

Formulate your questions precisely to get better answers:

| Instead of... | Better... |
|-------------|-----------|
| "Explain the document" | "Summarize Chapter 3 on sorting algorithms in three points" |
| "What is in it?" | "According to this document, what are the differences between Quicksort and Mergesort?" |
| "How does that work?" | "Explain the Heapsort algorithm step-by-step using the document" |

!!! tip "Use Follow-up Questions"
    The chat understands conversation context. Use follow-up questions like
    "Explain that in more detail" or "Give me an example of that".

## Next Steps

- [:octicons-arrow-right-24: Manage Documents](documents.md)
- [:octicons-arrow-right-24: Generate Questions from Documents](rag-exam.md)
- [:octicons-arrow-right-24: Manage Subscription](subscription.md)
