# Best Practices

## Document Upload

### Optimal Preparation

1. Structure documents with clear headings
2. Use consistent formatting
3. Add metadata (title, author, date)
4. Avoid watermarks and background images

### Batch Upload

Upload related documents together (e.g., all chapters of a textbook). This makes later RAG exams easier.

## Question Creation

### Topic Formulation

- Specific rather than general
- Provide context
- Keep Bloom's level in mind

!!! example "Examples"
    **Good:**

    - "Python Lists – Methods append(), extend(), insert()"
    - "Algorithms – Time Complexity of Sorting Methods"

    **Poor:**

    - "Python" (too broad)
    - "Programming" (too general)

### Quality Control

- Always review generated questions
- Pay attention to confidence scores
- Adjust difficulty levels accordingly
- Use source references for verification

## RAG Exams

- Select 3–5 relevant documents (optimal)
- Give a specific focus
- Too many documents lead to lower quality

## ChatBot Usage

Begin with overview questions and deepen progressively:

```text
User: "What is Heapsort?"
Bot: [Explains Heapsort]

User: "How does that differ from Quicksort?"
Bot: [Compares both algorithms]

User: "Which is more efficient for large datasets?"
Bot: [Analyzes complexity]
```

## Use Review Queue Effectively

- Review questions promptly after generation — context is fresher
- Use filter options (status, difficulty, question type) to keep the queue manageable
- **Rejecting is better than allowing bad questions**: Quality over quantity
- If many questions are rejected: Adjust prompt, improve source document, or refine topic
- Approve only questions you would ask yourself

## Exam Composer

- Plan exam structure before selecting questions: How many questions? Which types? What difficulty distribution?
- Mix question types (Multiple Choice + open-ended) for varied exams
- Export a test version and read it fully through before creating the final version
- Check automatic numbering and formatting in the exported document
