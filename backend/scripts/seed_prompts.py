"""
Seed script for initial prompts in the Knowledge Base.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from database import SessionLocal
from models.prompt import Prompt
from services.prompt_vector_service import PromptVectorService
import asyncio


async def seed_prompts():
    """Load initial prompts into the database"""
    db = SessionLocal()
    vector_service = PromptVectorService()

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

IMPORTANT: Base your answers ONLY on the provided document context. If the answer cannot be found in the documents, say so clearly.

Document Context:
{context}

Provide clear, accurate, and well-structured answers with citations to specific sections of the documents.

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
            "name": "system_prompt_question_evaluation",
            "content": """You are an expert in educational assessment and grading.

Your task is to evaluate student answers to exam questions based on provided evaluation criteria.

Question: {question}
Student Answer: {student_answer}
Evaluation Criteria: {criteria}

Provide a detailed evaluation including:
1. Score (0-100)
2. Grade (A/B/C/D/F)
3. Strengths of the answer
4. Areas for improvement
5. Specific feedback on each evaluation criterion

Be fair, consistent, and constructive in your feedback.""",
            "description": "System prompt for evaluating student answers",
            "category": "system_prompt",
            "use_case": "evaluation",
            "tags": ["grading", "feedback", "assessment"],
            "version": 1,
            "is_active": True,
        },
        {
            "name": "few_shot_example_bloom_level_3",
            "content": """Example Question (Bloom Level 3 - Application):

Topic: Sorting Algorithms
Question: "Given the following unsorted array [64, 34, 25, 12, 22, 11, 90], demonstrate how the QuickSort algorithm would sort this array. Show each step of the partitioning process and explain your choice of pivot element."

Evaluation Criteria:
- Correct identification of pivot element (2 points)
- Accurate partitioning steps (4 points)
- Clear explanation of the process (2 points)
- Final sorted array (2 points)

Sample Answer (Excellent):
"Using the last element (90) as pivot:
1. Partition: [64,34,25,12,22,11] | 90
2. Recursively sort left partition using 11 as pivot...
[Final sorted: 11, 12, 22, 25, 34, 64, 90]"

This demonstrates application of the algorithm to a specific problem.""",
            "description": "Few-shot example for Bloom Level 3 questions",
            "category": "few_shot_example",
            "use_case": "question_generation",
            "tags": ["bloom_level_3", "application", "algorithms"],
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

        # Create prompt
        prompt = Prompt(**prompt_data)
        db.add(prompt)
        db.flush()

        # Add to Qdrant
        try:
            point_id = await vector_service.add_prompt_to_index(prompt)
            prompt.qdrant_point_id = point_id
            print(f"✅ Created prompt: {prompt.name} (v{prompt.version})")
            created_count += 1
        except Exception as e:
            print(f"⚠️  Warning: Could not add to Qdrant: {e}")
            print(f"   Prompt created in DB but not indexed")
            created_count += 1

    db.commit()
    db.close()

    print(f"\n{'='*60}")
    print(f"✅ Prompt seeding completed!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {created_count + skipped_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("🌱 Starting prompt seeding...\n")
    asyncio.run(seed_prompts())

