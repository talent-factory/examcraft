# Create AI Exams

Generate exam questions on any topic — without uploaded documents.

## Configuration

### 1. Enter Exam Topic

Enter a specific topic:

!!! tip "Good Topic Formulation"
    - "Python Programming – Lists and Dictionaries"
    - "Data Structures – Heapsort Algorithm"

!!! warning "Avoid"
    - "Computer Science" (too general)
    - "Programming" (too broad)

### 2. Select Difficulty Level

| Level | Description | Bloom's Taxonomy |
|-------|-------------|-----------------|
| Easy | Basic understanding | Remember, Understand |
| Medium | Application and analysis | Apply, Analyze |
| Hard | Evaluation and creation | Evaluate, Create |

### 3. Set Number of Questions

- Minimum: 1 question
- Maximum: 20 questions
- Recommended: 5–10 questions per run

### 4. Select Question Types

- **Multiple Choice** – 4 answer options, 1 correct
- **Open-ended** – Free-text answers

### 5. Select Language

- **Deutsch** — Questions and answers in German
- **English** — Questions and answers in English

## Start Generation

1. Click **Generate Exam**
2. Wait 10–30 seconds
3. Progress indicator: "Generating exam..."

## Results

Each generated question includes:

- Question number and question text
- Answer options (for multiple choice)
- Correct answer (marked in green)
- Explanation/rationale
- Bloom level
- Difficulty (1–5)

## After Generation

The generated questions automatically appear in the **[Review Queue](review-queue.md)**.

There you can:
- Review each question individually
- Approve questions (made available for the exam composer) or reject them
- After review, assemble a complete exam in the **[Exam Composer](exam-composer.md)**

!!! tip "Tip: Review First, Then Compose"
    Take time with the Review Queue. Well-reviewed questions make the
    exam composer more efficient.

## Frequently Asked Questions about AI Exams

**How do AI exams differ from RAG-based exams?**

AI exams are generated on any topic without needing documents to be uploaded. RAG exams use your uploaded course materials as a source. Choose AI exams for general topic focus, RAG exams for content directly contained in your documents.

**Which difficulty level is optimal?**

It depends on the level of your student group. For beginners: Easy. For advanced students: Medium to Hard. A mix is also possible — generate multiple sets with different difficulty levels and combine them later in the exam composer.

**Can I edit generated questions later?**

Yes! In the Review Queue you can review each question. Before you approve it, you can adjust the question text or answer options. Editing happens directly in the queue.

**How long does generation take?**

Typically 10–30 seconds for 5–10 questions, depending on topic, difficulty level, and server load. The progress indicator keeps you informed in real-time.

**Can I generate more than 20 questions?**

The maximum per run is 20 questions. For more questions: Run multiple generations in a row. New questions are added to the existing Review Queue.

## Tips for Better Results

- **Specific Topics**: The more specific the formulation, the better the quality. "Python Lists and Dictionaries" is better than just "Python".
- **Appropriate Difficulty Levels**: Choose difficulty levels that match your students' level of learning.
- **Regular Review**: Check questions promptly to ensure quality. The sooner you provide feedback, the better the AI adapts.
- **Achieve Variety**: Generate multiple runs with different difficulty levels and question types.
