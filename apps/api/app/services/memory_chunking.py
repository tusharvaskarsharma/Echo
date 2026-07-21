"""Story-preserving structured units and retrieval chunks for Emmy memories."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from app.models.memory import MemoryFragment


# A complete question/answer exchange always wins over a fixed length.  These
# limits apply only to ordinary prose paragraphs with several full sentences.
PREFERRED_CHUNK_CHARS = 1_200
MAX_CHUNKS_PER_MEMORY = 32

CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Family", ("father", "mother", "parent", "wife", "husband", "daughter", "son", "child", "children", "grandchild", "family")),
    ("Relationships", ("met ", "married", "marriage", "wife", "husband", "friend", "love", "relationship")),
    ("Childhood", ("childhood", "grew up", "school days", "when i was young", "young")),
    ("Career", ("work", "worked", "job", "career", "teacher", "workshop", "company", "retired", "profession")),
    ("Values", ("lesson", "honesty", "character", "resilience", "kindness", "value", "taught", "belief")),
    ("Advice", ("advice", "recommend", "should", "wish i knew", "lesson")),
    ("Preferences", ("hobby", "hobbies", "gardening", "garden", "music", "song", "tea", "enjoy", "like to")),
    ("Legacy", ("remember", "legacy", "grandchildren", "grandchild", "after i", "hope")),
    ("Stories", ("story", "remember when", "once", "one day", "regret", "proudest")),
    ("Identity", ("i am", "my name", "born", "identity")),
)

STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "for", "from", "how", "i", "in", "is",
    "it", "me", "my", "of", "on", "or", "that", "the", "their", "they", "to", "was", "what", "when", "who", "with", "you", "your",
})
SPEAKER_LINE = re.compile(r"^(?:emmy|interviewer|question|q|assistant|user|you|answer|a)\s*:\s*", re.IGNORECASE)
QUESTION_LINE = re.compile(r"^(?:emmy|interviewer|question|q|assistant)\s*:\s*(.+)$", re.IGNORECASE)
ANSWER_LINE = re.compile(r"^(?:user|you|answer|a)\s*:\s*(.+)$", re.IGNORECASE)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")
WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]{1,}")


@dataclass(frozen=True)
class MemoryChunk:
    chunk_index: int
    content: str
    category: str
    keywords: list[str]
    search_text: str

    @property
    def vector_id_suffix(self) -> str:
        return f"chunk-{self.chunk_index}"


@dataclass(frozen=True)
class StoryUnit:
    """A complete, independently retrievable life event or Q&A exchange."""

    content: str
    category: str
    keywords: list[str]
    title: str
    summary: str
    importance_score: float


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _paragraphs(text: str) -> list[str]:
    """Create atomic interview exchanges from paragraphs and speaker labels."""
    lines = [_normalise(line) for line in text.replace("\r\n", "\n").split("\n")]
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            # Retain line boundaries until the caller has paired a question
            # with its answer and derived its title/summary metadata.
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current.clear()

    for line in lines:
        if not line:
            flush()
            continue
        # A new interviewer prompt begins a new atomic exchange. Its answer
        # remains in the same unit, protecting the question's context.
        if QUESTION_LINE.match(line) and current:
            flush()
        current.append(line)
    flush()
    return blocks or ([_normalise(text)] if _normalise(text) else [])


def _sentence_groups(block: str) -> Iterable[str]:
    """Split a non-dialogue paragraph only between complete sentences."""
    if len(block) <= PREFERRED_CHUNK_CHARS:
        yield block
        return
    sentences = [part.strip() for part in SENTENCE_BREAK.split(block) if part.strip()]
    if len(sentences) < 2:
        yield block
        return
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        proposed_len = current_len + len(sentence) + (1 if current else 0)
        if current and proposed_len > PREFERRED_CHUNK_CHARS:
            yield " ".join(current)
            current, current_len = [], 0
        current.append(sentence)
        current_len += len(sentence) + (1 if current_len else 0)
    if current:
        yield " ".join(current)


def classify_category(text: str, fallback_topics: Iterable[str] = ()) -> str:
    haystack = f"{text} {' '.join(fallback_topics)}".lower()
    scores = {
        category: sum(haystack.count(keyword) for keyword in keywords)
        for category, keywords in CATEGORY_KEYWORDS
    }
    category, score = max(scores.items(), key=lambda item: item[1])
    return category if score else "Stories"


def extract_keywords(text: str, extra_terms: Iterable[str] = ()) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in [*extra_terms, *WORD.findall(text.lower())]:
        cleaned = _normalise(str(term).lower())
        if not cleaned or cleaned in STOP_WORDS or len(cleaned) < 2 or cleaned in seen:
            continue
        seen.add(cleaned)
        terms.append(cleaned)
    return terms[:32]


def _answer_text(exchange: str) -> str:
    answers = [match.group(1).strip() for line in exchange.split("\n") if (match := ANSWER_LINE.match(line.strip()))]
    if answers:
        return _normalise(" ".join(answers))
    # Lines have sometimes been normalised by a browser before persistence;
    # leave the full evidence untouched rather than guessing at a split.
    return _normalise(exchange)


def _title_for(exchange: str, category: str) -> str:
    for line in exchange.split("\n"):
        if match := QUESTION_LINE.match(line.strip()):
            question = match.group(1).strip().rstrip("?.!")
            return question[:100] or f"{category} memory"
    return f"{category} memory"


def _short_summary(text: str) -> str:
    sentences = [part.strip() for part in SENTENCE_BREAK.split(_normalise(text)) if part.strip()]
    summary = " ".join(sentences[:2]) or _normalise(text)
    return summary[:700].rstrip()


def importance_for_category(category: str) -> float:
    return {
        "Identity": 1.0, "Family": 0.96, "Relationships": 0.94, "Values": 0.94,
        "Legacy": 0.92, "Career": 0.86, "Childhood": 0.84, "Stories": 0.78,
        "Advice": 0.78, "Preferences": 0.66,
    }.get(category, 0.72)


def build_story_units(transcript: str, fallback_topics: Iterable[str] = ()) -> list[StoryUnit]:
    """Split an interview into complete, user-visible structured memories."""
    units: list[StoryUnit] = []
    for exchange in _paragraphs(transcript):
        pieces = [exchange] if SPEAKER_LINE.search(exchange) else list(_sentence_groups(exchange))
        for piece in pieces:
            content = _normalise(piece)
            if not content:
                continue
            category = classify_category(content, fallback_topics)
            answer = _answer_text(piece)
            units.append(StoryUnit(
                content=content,
                category=category,
                keywords=extract_keywords(content, [*fallback_topics, category]),
                title=_title_for(piece, category),
                summary=_short_summary(answer),
                importance_score=importance_for_category(category),
            ))
    return units[:MAX_CHUNKS_PER_MEMORY]


def _metadata_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("title", "summary", "context", "category", "importance_level"):
        if metadata.get(key):
            values.append(str(metadata[key]))
    for key in ("important_facts", "user_preferences", "people", "places", "objects", "topics", "keywords", "tags"):
        value = metadata.get(key, [])
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return values


def _search_text(content: str, category: str, keywords: list[str], metadata: dict[str, Any]) -> str:
    """Search the concise summary and metadata, then retain source evidence."""
    title = str(metadata.get("title") or "Preserved memory")
    summary = str(metadata.get("summary") or "")
    facts = "; ".join(str(item) for item in _normalise_metadata_list(metadata.get("important_facts")))
    people = ", ".join(str(item) for item in _normalise_metadata_list(metadata.get("people")))
    return _normalise(
        f"Title: {title}. Summary: {summary}. Category: {category}. "
        f"Facts: {facts}. People: {people}. Tags: {', '.join(keywords)}. Source evidence: {content}"
    )


def _normalise_metadata_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_memory_chunks(memory: MemoryFragment) -> list[MemoryChunk]:
    """Build stable chunks from canonical evidence and its structured summary."""
    source = memory.content.strip()
    if not source:
        return []

    metadata = memory.semantic_metadata if isinstance(memory.semantic_metadata, dict) else {}
    metadata_keywords = metadata.get("keywords", []) if isinstance(metadata.get("keywords"), list) else []
    metadata_tags = metadata.get("tags", []) if isinstance(metadata.get("tags"), list) else []
    expanded: list[str] = []
    for paragraph in _paragraphs(source):
        if SPEAKER_LINE.search(paragraph):
            expanded.append(paragraph)
        else:
            expanded.extend(_sentence_groups(paragraph))

    chunks: list[MemoryChunk] = []
    for text in expanded[:MAX_CHUNKS_PER_MEMORY]:
        category = str(metadata.get("category") or classify_category(text, memory.topics))
        keywords = extract_keywords(text, [*memory.topics, *memory.people_mentioned, *metadata_keywords, *metadata_tags, category])
        chunks.append(MemoryChunk(
            chunk_index=len(chunks), content=text, category=category, keywords=keywords,
            search_text=_search_text(text, category, keywords, metadata),
        ))
    return chunks
