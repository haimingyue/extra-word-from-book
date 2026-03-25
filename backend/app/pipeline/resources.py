from __future__ import annotations

import csv
import re
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def load_lemma_dict() -> dict[str, str]:
    settings = get_settings()
    lemma_dict: dict[str, str] = {
        "was": "be",
        "am": "be",
        "is": "be",
        "are": "be",
    }

    with settings.ecdict_file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            word = row["word"].lower()
            exchange = row.get("exchange", "").strip()
            if not exchange:
                continue
            match = re.search(r"(^|/)0:([^/]+)", exchange)
            if match:
                lemma = match.group(2)
                if lemma and lemma != word:
                    lemma_dict[word] = lemma
    return lemma_dict


@lru_cache
def load_coca_rank_dict() -> dict[str, int]:
    settings = get_settings()
    rank_dict: dict[str, int] = {}

    with settings.coca_words_file_path.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            word = row["Word"].lower()
            rank_value = row.get("COCA_Rank", "").strip()
            if not rank_value:
                continue
            rank = int(rank_value)
            if word not in rank_dict:
                rank_dict[word] = rank
    return rank_dict


@lru_cache
def load_exam_level_dict() -> dict[str, frozenset[str]]:
    settings = get_settings()
    exam_level_dict: dict[str, set[str]] = {}
    valid_labels = {"小学", "初中", "高中", "四级", "六级", "考研", "GRE", "TOEFL"}

    with settings.coca_words_file_path.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            word = row["Word"].lower()
            raw_exam_level = row.get("Exam_Level", "").strip()
            tags = {part.strip() for part in raw_exam_level.split("、") if part.strip() in valid_labels}
            if not tags:
                continue
            exam_level_dict.setdefault(word, set()).update(tags)

    return {word: frozenset(tags) for word, tags in exam_level_dict.items()}


@lru_cache
def load_dictionary_words() -> set[str]:
    settings = get_settings()
    words: set[str] = set()

    with settings.ecdict_file_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            word = row["word"].strip().lower()
            if word:
                words.add(word)
    return words
