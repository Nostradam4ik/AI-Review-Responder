"""AI-powered batch review analysis for Business Intelligence Reports."""
import json
import logging

from app.models.review import Review

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a professional business analyst specializing in customer experience. You analyze customer reviews and produce actionable business intelligence reports.

Analyze the provided reviews and return ONLY valid JSON with this exact structure — no markdown, no explanation, just JSON:

{
  "business_type": "restaurant",
  "overall_sentiment": "mixed",
  "avg_rating": 3.8,
  "nps_estimate": 12,

  "summary": "2-3 sentence executive summary of the period",

  "complaints": [
    {
      "category": "Service Speed",
      "mention_count": 12,
      "percentage": 28,
      "severity": "high",
      "trend": "worsening",
      "example_quotes": ["waited 45 min", "staff ignored us"],
      "root_cause": "Understaffed during peak hours (12-2pm, 7-9pm)",
      "recommendation": "Hire 2 part-time staff for lunch and dinner rush",
      "impact": "Fixing this could improve avg rating by ~0.4★"
    }
  ],

  "praises": [
    {
      "category": "Food Quality",
      "mention_count": 18,
      "percentage": 43,
      "example_quotes": ["pasta was incredible", "best pizza in town"],
      "recommendation": "Leverage in marketing — highlight signature dishes"
    }
  ],

  "urgent_alerts": [
    "3 reviews this week mention food poisoning — requires immediate investigation"
  ],

  "opportunities": [
    "15 customers asked about delivery — consider adding delivery service"
  ],

  "comparison": {
    "vs_previous_period": "Rating dropped from 4.1 to 3.8 (-0.3★)",
    "response_rate": "You responded to 68% of reviews (industry avg: 45%)"
  },

  "action_plan": [
    {
      "priority": 1,
      "action": "Address service speed immediately",
      "effort": "medium",
      "expected_impact": "high",
      "timeframe": "2 weeks"
    },
    {
      "priority": 2,
      "action": "Respond to all unanswered 1-2★ reviews",
      "effort": "low",
      "expected_impact": "medium",
      "timeframe": "this week"
    }
  ]
}

Business categories to detect automatically based on review content:
restaurant, hotel, retail, salon/spa, medical, automotive, other.

Severity levels: high (7+ mentions or safety issue), medium (3-6), low (1-2).
Trend: worsening / stable / improving (compare first half vs second half of the period).
"""


def _format_reviews(reviews: list[Review], max_count: int = 150) -> str:
    """Format reviews as numbered list for the LLM prompt."""
    def sort_key(r: Review):
        return r.review_date or r.synced_at

    sorted_reviews = sorted(reviews, key=sort_key, reverse=True)[:max_count]
    lines = []
    for i, r in enumerate(sorted_reviews, 1):
        comment = (r.comment or "")[:300]
        lines.append(f"[{i}] ★{r.rating} | {comment}")
    return "\n".join(lines) if lines else "No reviews available."


def _minimal_fallback(total: int, avg: float | None) -> dict:
    return {
        "business_type": "other",
        "overall_sentiment": "mixed",
        "avg_rating": round(avg, 1) if avg else 0.0,
        "nps_estimate": 0,
        "summary": f"Analysis based on {total} reviews. Detailed breakdown unavailable.",
        "complaints": [],
        "praises": [],
        "urgent_alerts": [],
        "opportunities": [],
        "comparison": {"vs_previous_period": "N/A", "response_rate": "N/A"},
        "action_plan": [],
    }


async def generate_intelligence_report(
    reviews: list[Review],
    period_label: str,
    location_name: str,
    previous_period_reviews: list[Review],
    groq_client,
) -> dict:
    """Call LLM to produce structured JSON analysis of a batch of reviews."""
    if not reviews:
        return _minimal_fallback(0, None)

    avg = sum(r.rating for r in reviews) / len(reviews)
    prev_avg = (
        sum(r.rating for r in previous_period_reviews) / len(previous_period_reviews)
        if previous_period_reviews
        else None
    )

    reviews_text = _format_reviews(reviews)
    prev_text = (
        _format_reviews(previous_period_reviews, max_count=50)
        if previous_period_reviews
        else "No data for comparison."
    )

    user_content = (
        f"Location: {location_name}\n"
        f"Period: {period_label}\n"
        f"Total reviews this period: {len(reviews)}\n"
        f"Previous period reviews: {len(previous_period_reviews)}"
    )
    if prev_avg is not None:
        user_content += f" (avg rating: {prev_avg:.1f}★)"
    user_content += f"\n\n--- CURRENT PERIOD REVIEWS ---\n{reviews_text}"
    if previous_period_reviews:
        user_content += f"\n\n--- PREVIOUS PERIOD REVIEWS (for comparison) ---\n{prev_text}"

    try:
        response = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4096,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("Intelligence report JSON parse failed: %s", e)
        return _minimal_fallback(len(reviews), avg)
    except Exception as e:
        logger.error("Intelligence report LLM call failed: %s", e)
        return _minimal_fallback(len(reviews), avg)
