from dataclasses import dataclass


@dataclass(slots=True)
class WordFrequencyItem:
    word: str
    book_frequency: int


@dataclass(slots=True)
class ResolvedWordItem:
    word: str
    lemma: str | None
    book_frequency: int
    coca_rank: int | None
    is_known: bool = False
