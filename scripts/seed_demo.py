from datetime import datetime, timedelta, timezone
from .models import ConsentLevel, MemoryFragment, Session


SUBJECT = {
    "id": "eleanor-74",
    "name": "Eleanor Williams",
    "age": 74,
    "voice": "nova",
    "bio": "A warm retired teacher who values family, faith, curiosity, and hard work.",
}

SESSION_TITLES = [
    "Growing up by the coast",
    "Learning and leaving home",
    "Family traditions",
    "Teaching years",
    "Love and resilience",
    "What I hope you remember",
]

RAW_MEMORIES = [
    ("I saved for two summers to take a train through Portugal in 1974, but my father became ill and I stayed home without regret.", "regret", "travel", ["father"], "1970s"),
    ("The postcard for Portugal stayed in my dresser for years because it reminded me that family came before a ticket.", "tenderness", "family", ["father"], "1970s"),
    ("I still dream about the blue tiles in Lisbon from the guidebook I read until the spine cracked.", "wonder", "travel", [], "1970s"),
    ("My mother taught me that a crowded kitchen is a sign of a rich life.", "joy", "family", ["mother"], "1950s"),
    ("I almost did not go to college because Dad was sick, but he made me promise to keep learning.", "pride", "education", ["father"], "1960s"),
    ("The first classroom I taught in had peeling paint and twenty-seven children who made me brave.", "pride", "career", [], "1970s"),
    ("Every Friday I made cinnamon rolls before the grandchildren came over.", "joy", "family", ["grandchildren"], "1990s"),
    ("I learned to drive in my brother's old truck with no radio and very patient nerves.", "humor", "growing up", ["brother"], "1960s"),
    ("Our family sang badly but loudly while washing the supper dishes.", "joy", "family", [], "1950s"),
    ("When I was frightened before a new term, I polished my shoes and remembered I belonged in that room.", "courage", "career", [], "1980s"),
    ("I kept every thank-you note from my students in a cedar box.", "gratitude", "career", ["students"], "1980s"),
    ("My sister and I could settle any argument with a walk by the river.", "love", "family", ["sister"], "1960s"),
    ("The best advice I gave students was to stay curious longer than feels comfortable.", "wisdom", "values", ["students"], "1990s"),
    ("I was proudest when a quiet child discovered they had something worth saying.", "pride", "career", ["students"], "1990s"),
    ("We planted tomatoes every spring even when the rabbits had other plans.", "humor", "home", [], "1980s"),
    ("After my father died, I finally took a small trip to the coast and learned grief can travel beside joy.", "grief", "family", ["father"], "1980s"),
    ("A good apology starts before the word sorry, with listening.", "wisdom", "values", [], "2000s"),
    ("I kept a blue teacup for guests because ordinary days deserve ceremony.", "joy", "home", [], "1990s"),
    ("The library was my first passport because every shelf let me leave town.", "wonder", "education", [], "1950s"),
    ("I never wanted a big house, only a table with enough chairs.", "contentment", "values", [], "1980s"),
    ("My brother mailed me a cassette from every city he visited, so I travelled through his stories.", "love", "family", ["brother"], "1970s"),
    ("I said yes to teaching because one teacher saw me when I was shy.", "gratitude", "career", ["Mrs. Lewis"], "1960s"),
    ("Faith was never an answer book to me; it was the courage to keep asking kind questions.", "faith", "values", [], "1990s"),
    ("I learned that being useful is not the same as being busy.", "wisdom", "values", [], "2000s"),
    ("The first time my granddaughter read a whole page aloud, I cried in the grocery store later.", "joy", "family", ["granddaughter"], "2000s"),
    ("I made soup for neighbours because a pot on the stove is a small way to say you are not alone.", "care", "community", ["neighbours"], "1990s"),
    ("My mother could make a dress from a curtain and confidence from nothing at all.", "admiration", "family", ["mother"], "1950s"),
    ("I was never good at resting until gardening taught me that nothing blooms by being hurried.", "wisdom", "home", [], "2000s"),
    ("The sea always made me feel like my worries had somewhere larger to go.", "peace", "place", [], "1960s"),
    ("I took my students outside whenever the lesson felt too small for the weather.", "joy", "career", ["students"], "1980s"),
    ("My father laughed with his whole shoulders, and I try to remember that kind of laughter.", "love", "family", ["father"], "1950s"),
    ("The hardest part of getting older is seeing how quickly a year can become a story.", "reflection", "aging", [], "2010s"),
    ("I told every child in my class that mistakes are proof they were brave enough to begin.", "encouragement", "career", ["students"], "1990s"),
    ("We had very little money, but no one was allowed to leave breakfast hungry.", "resilience", "family", [], "1950s"),
    ("I wore yellow to every important interview because it made me feel like sunshine had my back.", "humor", "career", [], "1970s"),
    ("The family recipe book is mostly stains, notes, and people remembering differently.", "joy", "family", [], "2000s"),
    ("I wish I had called old friends sooner, but I am grateful for every call I finally made.", "regret", "friendship", [], "2010s"),
    ("When the town flooded, neighbours passed food along the street before anyone asked.", "gratitude", "community", ["neighbours"], "1980s"),
    ("I learned patience from children and punctuality from buses, usually in that order.", "humor", "career", ["students"], "1980s"),
    ("A home should have music, a drawer of batteries, and room for one more person.", "contentment", "values", [], "2000s"),
    ("I am proud that our family tells the truth gently, even when it is difficult.", "pride", "values", ["family"], "2010s"),
    ("The most important thing I know is that love is a practice, not only a feeling.", "love", "values", [], "2010s"),
]


def build_sessions() -> list[Session]:
    start = datetime(2024, 3, 14, tzinfo=timezone.utc)
    return [Session(id=f"session-{index + 1}", subject_id=SUBJECT["id"], title=title, status="completed", recorded_at=start + timedelta(days=index * 21)) for index, title in enumerate(SESSION_TITLES)]


def build_memories() -> list[MemoryFragment]:
    sessions = build_sessions()
    memories: list[MemoryFragment] = []
    for index, (content, emotion, topic, people, era) in enumerate(RAW_MEMORIES):
        session = sessions[index % len(sessions)]
        consent = ConsentLevel.FAMILY
        if index in {14, 31}:
            consent = ConsentLevel.PRIVATE
        elif index in {22, 39}:
            consent = ConsentLevel.LEGACY
        memories.append(MemoryFragment(
            id=f"memory-{index + 1:02d}", session_id=session.id, content=content,
            emotion_tags=[emotion], people_mentioned=people, topics=[topic], time_period=era,
            confidence_score=round(0.78 + ((index % 7) * 0.03), 2), consent_level=consent,
            recorded_at=session.recorded_at, timestamp_seconds=45 + index * 31,
            x=float(8 + ((index * 19) % 84)), y=float(12 + ((index * 31) % 76)),
        ))
    return memories

