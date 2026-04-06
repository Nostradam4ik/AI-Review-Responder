from groq import AsyncGroq

from .base import LLMProvider, ReviewContext

TONE_INSTRUCTIONS = {
    "formal": "professional and formal",
    "warm": "friendly and warm",
    "casual": "casual and relaxed",
}


class GroqProvider(LLMProvider):
    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def generate_response(self, context: ReviewContext) -> str:
        tone_desc = TONE_INSTRUCTIONS[context.tone]

        system_prompt = (
            f'You are a {tone_desc} customer service manager '
            f'for "{context.business_name}". '
            "CRITICAL RULES:\n"
            "- Respond in the EXACT same language as the review\n"
            "- Keep response under 150 words\n"
            "- Be specific to what the customer mentioned\n"
            '- Never use generic phrases like "Thank you for your feedback"\n'
            "- For 1-2 star reviews: empathize and offer solution\n"
            "- For 4-5 star reviews: be grateful and reinforce positives"
        )
        if context.extra_instructions:
            system_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{context.extra_instructions}"

        response = await self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Review ({context.rating}/5 stars):\n{context.review_text}"},
            ],
            max_tokens=250,
            temperature=0.75,
        )
        return response.choices[0].message.content
