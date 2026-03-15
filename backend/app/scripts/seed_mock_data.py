"""Seed mock data for testing without a real Google Business Profile."""
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.models.location import Location
from app.models.review import Review

MOCK_REVIEWS = [
    # 5 stars - French
    {
        "gmb_review_id": "mock_review_001",
        "author_name": "Marie Dupont",
        "rating": 5,
        "comment": "Excellent restaurant ! La cuisine est vraiment exceptionnelle, les plats sont savoureux et la présentation est magnifique. Le service est impeccable et l'atmosphère très agréable. Je recommande vivement !",
        "language": "fr",
        "days_ago": 2,
    },
    {
        "gmb_review_id": "mock_review_002",
        "author_name": "Pierre Martin",
        "rating": 5,
        "comment": "Une expérience culinaire inoubliable ! Le chef propose des plats créatifs avec des produits frais et locaux. Le personnel est chaleureux et attentionné. Nous reviendrons certainement !",
        "language": "fr",
        "days_ago": 5,
    },
    {
        "gmb_review_id": "mock_review_003",
        "author_name": "Sophie Bernard",
        "rating": 5,
        "comment": "Coup de cœur pour ce bistrot ! Ambiance authentique parisienne, cuisine traditionnelle revisitée avec talent. Le foie gras et le magret de canard étaient divins. Prix très raisonnables.",
        "language": "fr",
        "days_ago": 8,
    },
    # 4 stars - French
    {
        "gmb_review_id": "mock_review_004",
        "author_name": "Jean-Luc Moreau",
        "rating": 4,
        "comment": "Très bon restaurant dans l'ensemble. La nourriture était délicieuse et le service attentif. Seul bémol : l'attente un peu longue entre les plats. Mais on y reviendra sans hésiter.",
        "language": "fr",
        "days_ago": 10,
    },
    {
        "gmb_review_id": "mock_review_005",
        "author_name": "Isabelle Petit",
        "rating": 4,
        "comment": "Bonne adresse à Paris. La carte est variée et les portions généreuses. Le dessert maison était succulent. L'endroit est un peu bruyant le week-end mais ça reste agréable.",
        "language": "fr",
        "days_ago": 14,
    },
    # 3 stars - Mixed
    {
        "gmb_review_id": "mock_review_006",
        "author_name": "François Leroy",
        "rating": 3,
        "comment": "Restaurant correct sans plus. La cuisine est honnête mais sans grande surprise. Le service était un peu froid ce soir-là. À tenter peut-être lors d'une autre occasion.",
        "language": "fr",
        "days_ago": 18,
    },
    {
        "gmb_review_id": "mock_review_007",
        "author_name": "Nathalie Simon",
        "rating": 3,
        "comment": "Expérience mitigée. L'entrée était excellente mais le plat principal était trop salé. Le cadre est sympa et le personnel souriant. Peut mieux faire pour le prix demandé.",
        "language": "fr",
        "days_ago": 22,
    },
    # 1-2 stars - Complaints
    {
        "gmb_review_id": "mock_review_008",
        "author_name": "Robert Girard",
        "rating": 2,
        "comment": "Déçu par cette visite. Nous avons attendu 45 minutes pour être servis. Le steak était trop cuit malgré notre demande saignant. La facture ne correspondait pas à la qualité du repas.",
        "language": "fr",
        "days_ago": 25,
    },
    {
        "gmb_review_id": "mock_review_009",
        "author_name": "Céline Rousseau",
        "rating": 1,
        "comment": "Très mauvaise expérience. Personnel désagréable et peu professionnel. Nous avons trouvé un cheveu dans notre plat et le serveur n'a pas semblé s'en préoccuper. Je ne reviendrai pas.",
        "language": "fr",
        "days_ago": 30,
    },
    # 5 stars - English
    {
        "gmb_review_id": "mock_review_010",
        "author_name": "James Wilson",
        "rating": 5,
        "comment": "Absolutely fantastic bistrot! We stumbled upon this gem during our Paris trip and couldn't be happier. Authentic French cuisine, cozy atmosphere, and incredibly friendly staff. The escargots were outstanding!",
        "language": "en",
        "days_ago": 3,
    },
]


async def seed_mock_data(db: AsyncSession) -> dict:
    """Insert mock user, location, and reviews. Returns summary."""
    # Check if already seeded
    existing = await db.execute(
        select(User).where(User.email == "test@test.com")
    )
    user = existing.scalar_one_or_none()

    if user is None:
        user = User(
            email="test@test.com",
            business_name="Le Petit Bistrot Paris",
            google_id="mock_google_123",
            access_token="mock_token",
            tone_preference="warm",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    # Create Pro trial subscription for mock user (if not exists)
    sub_result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    if sub_result.scalar_one_or_none() is None:
        db.add(Subscription(
            user_id=user.id,
            plan_id="pro",
            status="trialing",
            trial_end=datetime.now(timezone.utc) + timedelta(days=14),
        ))
        await db.flush()

    # Check/create location
    loc_result = await db.execute(
        select(Location).where(Location.gmb_location_id == "mock_location_001")
    )
    location = loc_result.scalar_one_or_none()

    if location is None:
        location = Location(
            user_id=user.id,
            gmb_location_id="mock_location_001",
            name="Le Petit Bistrot Paris",
            address="12 Rue de Rivoli, 75001 Paris",
            is_active=True,
        )
        db.add(location)
        await db.flush()
        await db.refresh(location)

    # Insert reviews (skip existing)
    created = 0
    for r in MOCK_REVIEWS:
        existing_review = await db.execute(
            select(Review).where(Review.gmb_review_id == r["gmb_review_id"])
        )
        if existing_review.scalar_one_or_none() is not None:
            continue

        review = Review(
            location_id=location.id,
            gmb_review_id=r["gmb_review_id"],
            author_name=r["author_name"],
            rating=r["rating"],
            comment=r["comment"],
            language=r["language"],
            review_date=datetime.now(timezone.utc) - timedelta(days=r["days_ago"]),
            status="pending",
        )
        db.add(review)
        created += 1

    return {
        "user_email": user.email,
        "location": location.name,
        "reviews_created": created,
    }
