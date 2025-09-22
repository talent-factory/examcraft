"""
Claude API Service for ExamCraft AI
Handles communication with Anthropic's Claude API for intelligent question generation
"""

import os
import httpx
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service for interacting with Claude API"""
    
    def __init__(self):
        self.api_key = os.getenv("CLAUDE_API_KEY")
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-sonnet-20240229"
        
    async def generate_questions(
        self, 
        topic: str, 
        difficulty: str = "medium",
        question_count: int = 5,
        question_types: List[str] = None,
        language: str = "de"
    ) -> List[Dict[str, Any]]:
        """
        Generate exam questions using Claude API
        
        Args:
            topic: The subject/topic for the questions
            difficulty: easy, medium, or hard
            question_count: Number of questions to generate
            question_types: Types of questions (multiple_choice, open_ended, etc.)
            language: Language for questions (de, en)
            
        Returns:
            List of generated questions
        """
        
        if not self.api_key:
            logger.warning("Claude API key not configured, using demo questions")
            return self._generate_demo_questions(topic, difficulty, question_count, language)
        
        try:
            prompt = self._build_prompt(topic, difficulty, question_count, question_types, language)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 2000,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"]
                    return self._parse_claude_response(content, topic, difficulty)
                else:
                    logger.error(f"Claude API error: {response.status_code} - {response.text}")
                    return self._generate_demo_questions(topic, difficulty, question_count, language)
                    
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return self._generate_demo_questions(topic, difficulty, question_count, language)
    
    def _build_prompt(
        self, 
        topic: str, 
        difficulty: str, 
        question_count: int, 
        question_types: List[str],
        language: str
    ) -> str:
        """Build the prompt for Claude API"""
        
        lang_instruction = "auf Deutsch" if language == "de" else "in English"
        difficulty_map = {
            "easy": "einfach" if language == "de" else "easy",
            "medium": "mittel" if language == "de" else "medium", 
            "hard": "schwer" if language == "de" else "hard"
        }
        
        prompt = f"""
Erstelle {question_count} Prüfungsfragen zum Thema "{topic}" {lang_instruction}.

Anforderungen:
- Schwierigkeitsgrad: {difficulty_map.get(difficulty, difficulty)}
- Mischung aus Multiple-Choice und offenen Fragen
- Jede Frage soll lehrreich und praxisbezogen sein
- Für Multiple-Choice: 4 Antwortoptionen mit einer korrekten Antwort
- Für offene Fragen: Klare Fragestellung mit Bewertungskriterien

Format als JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "multiple_choice",
      "question": "Fragetext hier",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Erklärung warum diese Antwort korrekt ist",
      "difficulty": "{difficulty}",
      "topic": "{topic}"
    }},
    {{
      "id": "q2", 
      "type": "open_ended",
      "question": "Offene Fragestellung hier",
      "options": null,
      "correct_answer": null,
      "explanation": "Bewertungskriterien und Musterlösung",
      "difficulty": "{difficulty}",
      "topic": "{topic}"
    }}
  ]
}}

Wichtig: Antworte nur mit dem JSON, keine zusätzlichen Erklärungen.
"""
        return prompt
    
    def _parse_claude_response(self, content: str, topic: str, difficulty: str) -> List[Dict[str, Any]]:
        """Parse Claude's JSON response"""
        try:
            # Try to extract JSON from the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
                return data.get("questions", [])
            else:
                logger.error("No valid JSON found in Claude response")
                return self._generate_demo_questions(topic, difficulty, 3, "de")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return self._generate_demo_questions(topic, difficulty, 3, "de")
    
    def _generate_demo_questions(
        self, 
        topic: str, 
        difficulty: str, 
        question_count: int,
        language: str = "de"
    ) -> List[Dict[str, Any]]:
        """Generate demo questions when Claude API is not available"""
        
        demo_questions = []
        
        # Multiple Choice Question
        demo_questions.append({
            "id": "demo_q1",
            "type": "multiple_choice",
            "question": f"Was ist ein wichtiger Aspekt von {topic}?",
            "options": [
                "Option A: Grundlegendes Verständnis",
                "Option B: Praktische Anwendung", 
                "Option C: Theoretische Fundierung",
                "Option D: Alle oben genannten"
            ],
            "correct_answer": "Option D: Alle oben genannten",
            "explanation": "Alle Aspekte sind wichtig für ein vollständiges Verständnis des Themas.",
            "difficulty": difficulty,
            "topic": topic
        })
        
        # Open Ended Question
        demo_questions.append({
            "id": "demo_q2",
            "type": "open_ended",
            "question": f"Erklären Sie die praktische Bedeutung von {topic} in der realen Welt. Geben Sie konkrete Beispiele.",
            "options": None,
            "correct_answer": None,
            "explanation": "Eine gute Antwort sollte praktische Anwendungen aufzeigen und konkrete Beispiele nennen. Bewertungskriterien: Verständnis (40%), Beispiele (30%), Struktur (30%).",
            "difficulty": difficulty,
            "topic": topic
        })
        
        # Additional questions based on count
        if question_count > 2:
            demo_questions.append({
                "id": "demo_q3",
                "type": "multiple_choice",
                "question": f"Welche Herausforderung ist typisch beim Erlernen von {topic}?",
                "options": [
                    "Option A: Komplexität der Konzepte",
                    "Option B: Mangel an Praxisbezug",
                    "Option C: Schnelle Entwicklung des Fachgebiets",
                    "Option D: Alle genannten Punkte"
                ],
                "correct_answer": "Option D: Alle genannten Punkte",
                "explanation": "Beim Erlernen komplexer Themen treten oft mehrere Herausforderungen gleichzeitig auf.",
                "difficulty": difficulty,
                "topic": topic
            })
        
        return demo_questions[:question_count]
