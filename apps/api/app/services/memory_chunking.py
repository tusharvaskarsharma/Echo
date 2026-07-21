"""Story-preserving chunks and retrieval metadata for archived memories.

The first version of Echo embedded an entire interview in one vector.  That
works for a short note, but an interview can contain many unrelated stories;
one vector cannot reliably represent every fact in it.  This module produces
small, readable evidence units without cutting through sentences or an
interview question/answer pair.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from app.models.memory import MemoryFragment


# A chunk is deliberately allowed to exceed the preferred size when it is one
# interview exchange.  Preserving a complete answer is more important than
# forcing a story through an arbitrary token boundary.
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
SPEAKER_LINE = re.compile(r"^(?:echo|interviewer|question|q|assistant|user|you|answer|a)\s*:\s*", re.IGNORECASE)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")
WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]{1,}")


@dataclass(frozen=True)
class MemoryChunk:
    chunk_index: int
    content: str
    category: str
    keywords: list[str]

    @property
    def vector_id_suffix(self) -> str:
        return f"chunk-{self.chunk_index}"


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _paragraphs(text: str) -> list[str]:
    """Create atomic interview exchanges from paragraphs and speaker labels."""
    lines = [_normalise(line) for line in text.replace("\r\n", "\n").split("\n")]
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            block = _normalise(" ".join(current))
            if block:
                blocks.append(block)
            current.clear()

    for line in lines:
        if not line:
            flush()
            continue
        # A new interviewer question starts a fresh exchange, but its answer
        # remains together with it.  This is the key distinction from token
        # slicing, which formerly separated the question from its evidence.
        if SPEAKER_LINE.match(line) and current and re.match(r"^(?:echo|interviewer|question|q|assistant)\s*:", line, re.IGNORECASE):
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
        # An unusually long single sentence is still kept intact.  A complete
        # sentence is safer evidence than a truncated fragment.
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


def build_memory_chunks(memory: MemoryFragment) -> list[MemoryChunk]:
    """Build stable chunks from a memory's canonical, unmodified evidence."""
    # Preserve newlines until after Q&A/paragraph detection.  Normalising the
    # whole transcript first would collapse every interview exchange into one
    # large block and defeat story-preserving chunking.
    source = memory.content.strip()
    if not source:
        return []

    metadata = memory.semantic_metadata or {}
    metadata_keywords = metadata.get("keywords", []) if isinstance(metadata, dict) else []
    expanded: list[str] = []
    for paragraph in _paragraphs(source):
        # Never split explicit Q&A/dialogue exchanges.  A normal long prose
        # paragraph is divided between sentences only.
        if SPEAKER_LINE.search(paragraph):
            expanded.append(paragraph)
        else:
            expanded.extend(_sentence_groups(paragraph))

    chunks: list[MemoryChunk] = []
    for text in expanded[:MAX_CHUNKS_PER_MEMORY]:
        category = classify_category(text, memory.topics)
        chunks.append(MemoryChunk(
            chunk_index=len(chunks),
            content=text,
            category=category,
            keywords=extract_keywords(text, [*memory.topics, *memory.people_mentioned, *metadata_keywords]),
        ))
    return chunks
