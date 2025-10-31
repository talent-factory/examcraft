"""
Seed script for initial prompts in the Knowledge Base.
Simplified version that works in Docker container.
"""

import sys
import os
from datetime import datetime

# Add app path for imports (Docker: /app)
app_path = '/app'
if os.path.exists(app_path) and app_path not in sys.path:
    sys.path.insert(0, app_path)

# Add premium path for imports
premium_path = '/app/premium'
if os.path.exists(premium_path) and premium_path not in sys.path:
    sys.path.insert(0, premium_path)

from sqlalchemy.orm import Session
from database import SessionLocal, Base


def seed_prompts():
    """Load initial prompts into the database"""
    db = SessionLocal()

    # Get Prompt model from SQLAlchemy registry (already imported in database.py)
    # This avoids double-registration issues
    try:
        # Try to get Prompt from the registry
        Prompt = None
        for mapper in Base.registry.mappers:
            if mapper.class_.__name__ == 'Prompt':
                Prompt = mapper.class_
                break

        if Prompt is None:
            # If not found in registry, try direct import
            from premium.models.prompt import Prompt
    except Exception as e:
        print(f"❌ Could not get Prompt model: {e}")
        db.close()
        return

    prompts_to_seed = [
        {
            "name": "system_prompt_question_generation_bloom",
            "content": """You are an expert in educational assessment and exam question generation. 
Your task is to create high-quality exam questions based on Bloom's Taxonomy.

Current Bloom Level: {bloom_level}
Topic: {topic}

Generate a question that:
1. Aligns with Bloom Taxonomy Level {bloom_level}
2. Is suitable for open-book examination format
3. Includes detailed evaluation criteria
4. Provides sample answers at A/B/C quality levels

Format your response as structured JSON with the following fields:
- question: The exam question text
- bloom_level: The Bloom taxonomy level (1-6)
- evaluation_criteria: List of criteria for grading
- sample_answers: Object with keys "excellent", "good", "acceptable"
- estimated_time_minutes: Estimated time to answer
- points: Suggested point value""",
            "description": "System prompt for Bloom Taxonomy-based question generation",
            "category": "system_prompt",
            "use_case": "question_generation",
            "tags": ["bloom_taxonomy", "openbook", "structured_output"],
            "version": 1,
            "is_active": True,
        },
        {
            "name": "system_prompt_chatbot_document_qa",
            "content": """You are a helpful assistant that answers questions based on uploaded documents.

Context from documents:
{context}

User question: {question}

When answering:
1. Quote relevant passages from the documents
2. Cite the source document and page/section number
3. If information is not in the documents, explicitly state this
4. Provide comprehensive answers that synthesize information from multiple sources if needed""",
            "description": "System prompt for document-based Q&A chatbot",
            "category": "system_prompt",
            "use_case": "chatbot",
            "tags": ["rag", "document_qa", "citations"],
            "version": 1,
            "is_active": True,
        },
        {
            "name": "default_prompt_multiple_choice",
            "content": """You are an expert in educational assessment and exam question generation.

Your task is to create a high-quality multiple-choice question based on the provided context.

Context:
{context}

Topic: {topic}
Difficulty: {difficulty}
Language: {language}

Generate a multiple-choice question that:
1. Tests understanding of key concepts from the context
2. Is suitable for open-book examination format
3. Has one clearly correct answer
4. Includes 3-4 plausible distractors (incorrect options)
5. Avoids ambiguity and trick questions

Format your response as structured JSON with the following fields:
- question_text: The question text
- options: Array of 4 answer options (strings)
- correct_answer: The correct option (exact match from options array)
- explanation: Detailed explanation of why the correct answer is right and why distractors are wrong
- difficulty: The difficulty level (easy/medium/hard)
- source_reference: Reference to the specific part of the context used""",
            "description": "Default system prompt for multiple-choice question generation",
            "category": "system_prompt",
            "use_case": "question_generation_multiple_choice",
            "tags": ["multiple_choice", "openbook", "default"],
            "version": 1,
            "is_active": True,
        },
        {
            "name": "default_prompt_open_ended",
            "content": """You are an expert in educational assessment and exam question generation.

Your task is to create a high-quality open-ended question based on the provided context.

Context:
{context}

Topic: {topic}
Difficulty: {difficulty}
Language: {language}

Generate an open-ended question that:
1. Requires critical thinking and analysis
2. Is suitable for open-book examination format
3. Cannot be answered with simple facts (requires synthesis and evaluation)
4. Has clear evaluation criteria
5. Allows for multiple valid approaches or perspectives

Format your response as structured JSON with the following fields:
- question_text: The question text
- evaluation_criteria: Array of criteria for grading (each with description and points)
- sample_answer: A high-quality example answer
- explanation: What makes a good answer to this question
- difficulty: The difficulty level (easy/medium/hard)
- estimated_time_minutes: Estimated time to answer (5-30 minutes)
- source_reference: Reference to the specific part of the context used""",
            "description": "Default system prompt for open-ended question generation",
            "category": "system_prompt",
            "use_case": "question_generation_open_ended",
            "tags": ["open_ended", "openbook", "default"],
            "version": 1,
            "is_active": True,
        },
        {
            "name": "default_prompt_true_false",
            "content": """You are an expert in educational assessment and exam question generation.

Your task is to create a high-quality true/false question based on the provided context.

Context:
{context}

Topic: {topic}
Difficulty: {difficulty}
Language: {language}

Generate a true/false question that:
1. Tests understanding of a specific concept or fact from the context
2. Is unambiguous (clearly true or clearly false)
3. Avoids double negatives and trick wording
4. Is suitable for open-book examination format
5. Includes a detailed explanation

Format your response as structured JSON with the following fields:
- question_text: The statement to evaluate (true or false)
- correct_answer: Either "true" or "false"
- explanation: Detailed explanation of why the statement is true or false, with reference to the context
- difficulty: The difficulty level (easy/medium/hard)
- source_reference: Reference to the specific part of the context used""",
            "description": "Default system prompt for true/false question generation",
            "category": "system_prompt",
            "use_case": "question_generation_true_false",
            "tags": ["true_false", "openbook", "default"],
            "version": 1,
            "is_active": True,
        },
    ]

    created_count = 0
    skipped_count = 0

    for prompt_data in prompts_to_seed:
        # Check if already exists
        existing = (
            db.query(Prompt).filter(Prompt.name == prompt_data["name"]).first()
        )
        if existing:
            print(f"⏭️  Prompt '{prompt_data['name']}' already exists, skipping...")
            skipped_count += 1
            continue

        # Create prompt (without Qdrant indexing for now)
        prompt = Prompt(**prompt_data)
        db.add(prompt)
        db.flush()
        
        print(f"✅ Created prompt: {prompt.name} (v{prompt.version})")
        created_count += 1

    db.commit()
    db.close()

    print(f"\n🎉 Seed completed: {created_count} prompts created, {skipped_count} skipped")


if __name__ == "__main__":
    seed_prompts()

