"""Utility functions for the sandbox application."""


def format_name(first: str, last: str) -> str:
    """Format a full name from first and last."""
    return f"{first} {last}"


def is_even(n: int) -> bool:
    """Check if a number is even."""
    return n & 1 == 0


def reverse_string(s: str) -> str:
    """Reverse a string."""
    return s[::-1]
