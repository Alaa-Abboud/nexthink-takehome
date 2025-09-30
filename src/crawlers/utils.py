from bs4 import BeautifulSoup
import re

def sanitize_to_text(raw_content: str) -> str:
    """
    Strip HTML/XML tags, scripts, styles, and return plain text.
    """
    if not raw_content:
        return ""

    # Parse with lxml (faster, safer for messy HTML)
    soup = BeautifulSoup(raw_content, "html.parser")

    # Remove scripts and styles
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Get text and collapse whitespace
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)  # normalize spaces

    return text