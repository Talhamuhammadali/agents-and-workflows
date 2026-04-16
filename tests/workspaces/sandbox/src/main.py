"""Entry point for the sandbox application."""


def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hi there, {name}!"


def subtract(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b


def main():
    logging.info(greet("World"))
    print(f"2 + 3 = {subtract(2, 3)}")


if __name__ == "__main__":
    main()
