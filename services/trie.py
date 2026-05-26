"""
Trie (Prefix Tree) implementation optimized for multi-word phrase matching.
Instead of character-based states, this Trie uses word tokens as states,
which makes it highly efficient for scanning natural language OCR text.
"""

from typing import Dict, List, Set, Tuple, Optional
import re


class TrieNode:
    """Represents a node in the Token-based Trie."""
    def __init__(self):
        # Maps token -> child TrieNode
        self.children: Dict[str, TrieNode] = {}
        # Stores tuples of (doc_type, full_keyword_phrase) when a keyword ends here
        self.matches: List[Tuple[str, str]] = []


class TokenTrie:
    """Trie structure optimized for matching multi-token phrases in text."""
    def __init__(self):
        self.root = TrieNode()
        self.max_phrase_length = 0

    def _tokenize(self, text: str) -> List[str]:
        """Normalize and tokenize text into clean alphanumeric words."""
        return re.findall(r'\b[a-z0-9]+(?:\.[a-z0-9]+)?\b', text.lower())

    def insert(self, keyword_phrase: str, doc_type: str) -> None:
        """
        Inserts a keyword phrase into the Trie.
        
        Args:
            keyword_phrase: The full string phrase (e.g. "income tax department")
            doc_type: The associated document type (e.g. "pan")
        """
        # Tokenize the keyword phrase
        tokens = self._tokenize(keyword_phrase)
        if not tokens:
            return

        self.max_phrase_length = max(self.max_phrase_length, len(tokens))
        
        current = self.root
        for token in tokens:
            if token not in current.children:
                current.children[token] = TrieNode()
            current = current.children[token]
        
        # Mark node as terminal and store the match meta
        current.matches.append((doc_type, keyword_phrase))

    def search_all_matches(self, text: str) -> Dict[str, Set[str]]:
        """
        Scans the text in a single pass and returns all matched keywords grouped by doc_type.
        
        Complexity: O(T * L) where T is text token count and L is max keyword phrase length.
        Since L is tiny (usually <= 5), this runs in O(T) linear time.
        
        Args:
            text: Large OCR text string to search
            
        Returns:
            Dict mapping doc_type -> set of matched keyword phrases
        """
        tokens = self._tokenize(text)
        matches_found: Dict[str, Set[str]] = {}
        
        if not tokens:
            return matches_found

        n = len(tokens)
        
        # Slide through each token position as a potential start of a keyword phrase
        for i in range(n):
            token = tokens[i]
            # Fast-path check: if token is not the start of any keyword, skip
            if token not in self.root.children:
                continue
                
            current = self.root.children[token]
            if current.matches:
                for doc_type, phrase in current.matches:
                    if doc_type not in matches_found:
                        matches_found[doc_type] = set()
                    matches_found[doc_type].add(phrase)
            
            # Lookahead up to the maximum possible keyword length
            limit = min(n, i + self.max_phrase_length)
            for j in range(i + 1, limit):
                next_token = tokens[j]
                if next_token not in current.children:
                    break
                current = current.children[next_token]
                
                # If this node marks the end of any keywords, record the matches
                if current.matches:
                    for doc_type, phrase in current.matches:
                        if doc_type not in matches_found:
                            matches_found[doc_type] = set()
                        matches_found[doc_type].add(phrase)
                        
        return matches_found
