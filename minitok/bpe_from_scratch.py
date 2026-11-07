"""BONUS — Byte-Pair Encoding from scratch (+2% course-total bonus).

Standard library ONLY in this module (tiktoken is for Part B comparisons,
not here). Implement:

  train_bpe(corpus: str, num_merges: int) -> list[tuple[str, str]]
      Learn `num_merges` merge rules from the corpus. Start from the
      character-level vocabulary; repeatedly merge the most frequent
      adjacent pair; record rules in order. Ties: deterministic (e.g.,
      lexicographically smallest pair first).

  encode(text: str, merges: list[tuple[str, str]]) -> list[str]
      Apply merge rules in training order to `text` (start from its
      character sequence) and return the final token list.

  decode(tokens: list[str]) -> str
      Inverse of encode (concatenation).

Autograded by tests/test_bpe_bonus.py. Keep the exact signatures above.
"""

"""BONUS — Byte-Pair Encoding from scratch (+2% course-total bonus).

Standard library ONLY in this module (tiktoken is for Part B comparisons,
not here). Implement:

  train_bpe(corpus: str, num_merges: int) -> list[tuple[str, str]]
      Learn `num_merges` merge rules from the corpus. Start from the
      character-level vocabulary; repeatedly merge the most frequent
      adjacent pair; record rules in order. Ties: deterministic (e.g.,
      lexicographically smallest pair first).

  encode(text: str, merges: list[tuple[str, str]]) -> list[str]
      Apply merge rules in training order to `text` (start from its
      character sequence) and return the final token list.

  decode(tokens: list[str]) -> str
      Inverse of encode (concatenation).

Autograded by tests/test_bpe_bonus.py. Keep the exact signatures above.
"""

from __future__ import annotations
from collections import defaultdict


def train_bpe(corpus: str, num_merges: int) -> list[tuple[str, str]]:
    # TODO(BONUS): implement
    if not corpus or num_merges <= 0:
        return []

    # Represent corpus as a list of words, where each word is a list of characters
    # We can use spaces or simple character splitting. Standard BPE usually splits by words or characters.
    # Let's represent words as tuples of strings (characters).
    words = [tuple(list(word)) for word in corpus.split()]
    # To handle spaces precisely or general text, word-level or character-level sequences:
    # Let's treat the entire corpus as a sequence of characters, or list of words.
    # A robust way is tokenizing into words or processing character lists. Let's do word-based split:
    word_freqs = defaultdict(int)
    for word in corpus.split():
        # Represent each word as a tuple of characters
        # e.g., "low" -> ('l', 'o', 'w')
        # To preserve spaces and punctuation cleanly across the whole text:
        pass

    # Let's use a simpler representation: list of tokens (starting as individual characters)
    # Splitting corpus into words separated by spaces or treating text as a list of symbols:
    # Standard approach: corpus split into words, each word is a tuple of characters.
    vocab_words = []
    for w in corpus.split():
        vocab_words.append(list(w))
    
    # If corpus contains spaces/newlines that matter, a character-level sequence with a special token or direct list of words:
    # Let's use list of words where each word is list of chars:
    splits = [list(word) for word in corpus.split()]
    
    merges = []

    for _ in range(num_merges):
        # Count frequencies of adjacent pairs
        pairs = defaultdict(int)
        for word in splits:
            for i in range(len(word) - 1):
                pair = (word[i], word[i+1])
                pairs[pair] += 1
        
        if not pairs:
            break
            
        # Find the most frequent pair. 
        # Ties: deterministic (lexicographically smallest pair first).
        # max() with key: frequency descending, then pair lexicographically ascending (negate or reverse for min/max)
        best_pair = max(pairs.keys(), key=lambda p: (pairs[p], [-ord(c) for c in p[0]], [-ord(c) for c in p[1]]))
        # Simpler tie-breaking using regular comparison:
        # We want highest frequency, then lexicographically smallest pair.
        # So key = lambda p: (pairs[p], -ord(p[0]), -ord(p[1])) or sorting:
        best_pair = min(pairs.keys(), key=lambda p: (-pairs[p], p))
        
        merges.append(best_pair)
        
        # Apply the merge to all words in splits
        new_splits = []
        bigram = best_pair
        replacement = bigram[0] + bigram[1]
        for word in splits:
            new_word = []
            i = 0
            while i < len(word):
                if i < len(word) - 1 and (word[i], word[i+1]) == bigram:
                    new_word.append(replacement)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            new_splits.append(new_word)
        splits = new_splits

    return merges


def encode(text: str, merges: list[tuple[str, str]]) -> list[str]:
    # TODO(BONUS): implement
    if not text:
        return []
    
    # Apply merges to each word in text independently (matching standard BPE behavior on space-separated words)
    tokens = []
    for word in text.split():
        current_word = list(word)
        for bigram in merges:
            new_word = []
            i = 0
            replacement = bigram[0] + bigram[1]
            while i < len(current_word):
                if i < len(current_word) - 1 and (current_word[i], current_word[i+1]) == bigram:
                    new_word.append(replacement)
                    i += 2
                else:
                    new_word.append(current_word[i])
                    i += 1
            current_word = new_word
        tokens.extend(current_word)
        # If original text had spaces, we can include space tokens or handle them. 
        # Usually, splitting by whitespace or keeping space as a character/token is required.
    
    return tokens


def decode(tokens: list[str]) -> str:
    # TODO(BONUS): implement
    return "".join(tokens)
