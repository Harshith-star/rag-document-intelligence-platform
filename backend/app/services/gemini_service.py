"""Gemini service using the Google GenAI SDK."""

from google import genai
from google.genai import types

from ..config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    EMBEDDING_MODEL,
)

client = genai.Client(api_key=GEMINI_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = []

    for text in texts:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
               task_type="RETRIEVAL_DOCUMENT"
            ),
        )

        embeddings.append(response.embeddings[0].values)

    return embeddings


def embed_query(query: str) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY"
        ),
    )

    return response.embeddings[0].values


def generate_answer(
    question: str,
    context: str,
    system_prompt: str | None = None,
) -> str:

    if system_prompt is None:
        system_prompt = (
            "Answer ONLY from the provided context. "
            "If the answer isn't present, say you don't know. "
            "Always cite the source document."
        )

    prompt = f"""
Context:
{context}

Question:
{question}

Answer:
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )

    return response.text