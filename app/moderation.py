"""
Content Moderation Utilities
Handles profanity filtering, URL detection, and content validation
"""

import re
import os
from typing import List, Tuple


def load_profanity_list() -> set:
    """
    Load profanity words from the profanity_list.txt file
    Returns a set of lowercase words
    """
    profanity_file = os.path.join(os.path.dirname(__file__), 'profanity_list.txt')
    profanity_words = set()

    try:
        with open(profanity_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    profanity_words.add(line.lower())
    except FileNotFoundError:
        print(f"Warning: Profanity list file not found at {profanity_file}")

    return profanity_words


# Load profanity list once at module import
PROFANITY_WORDS = load_profanity_list()


def contains_profanity(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains any profanity words
    Returns (has_profanity, list_of_found_words)
    """
    if not text:
        return False, []

    # Convert to lowercase and split into words
    words = re.findall(r'\b\w+\b', text.lower())

    # Find profanity words
    found_profanity = [word for word in words if word in PROFANITY_WORDS]

    return len(found_profanity) > 0, found_profanity


def contains_url(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains URLs or links
    Returns (has_url, list_of_found_urls)
    """
    if not text:
        return False, []

    # Regex patterns for URLs
    patterns = [
        r'https?://[^\s]+',  # http:// or https://
        r'www\.[^\s]+',  # www.something
        r'\b[a-zA-Z0-9-]+\.(com|net|org|io|co\.uk|edu|gov)[^\s]*',  # domain.tld
    ]

    found_urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found_urls.extend(matches)

    return len(found_urls) > 0, found_urls


def validate_comment_content(content: str) -> Tuple[bool, str]:
    """
    Validate comment content for profanity and URLs
    Returns (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "Comment cannot be empty"

    if len(content) > 5000:
        return False, "Comment is too long (maximum 5000 characters)"

    # Check for URLs
    has_url, urls = contains_url(content)
    if has_url:
        return False, f"Comments cannot contain URLs or links. Found: {', '.join(urls[:3])}"

    # Check for profanity
    has_profanity, profanity_words = contains_profanity(content)
    if has_profanity:
        return False, f"Comment contains inappropriate language. Please remove: {', '.join(profanity_words[:3])}"

    return True, ""


def sanitize_content(content: str) -> str:
    """
    Sanitize content by removing HTML tags and normalizing whitespace
    """
    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)

    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content)

    # Trim leading/trailing whitespace
    content = content.strip()

    return content
