import re
from app.services.constraints import validate_variant_content


def _clean_excerpt(markdown_text: str, max_chars: int = 160) -> str:
    plain = re.sub(r"[#*_`>~-]+", " ", markdown_text)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_chars:
        return plain
    shortened = plain[: max_chars - 3].rsplit(" ", 1)[0]
    return f"{shortened}..."


def generate_variant_text(platform: str, title: str | None, stored_content: str) -> str:
    heading = (title or "Post Update").strip()
    excerpt = _clean_excerpt(stored_content, max_chars=160)

    if platform == "telegram":
        text = (
            f"{heading}\n\n"
            f"{excerpt}\n\n"
            f"Full details inside. #Engineering #Backend"
        )
    elif platform == "mock_x":
        short_excerpt = _clean_excerpt(stored_content, max_chars=100)
        text = f"{heading}: {short_excerpt} #Backend #Dev"
    elif platform == "mock_linkedin":
        text = (
            f"{heading}\n\n"
            f"{excerpt}\n\n"
            f"What are your thoughts on applying this in production? #SoftwareEngineering #Architecture"
        )
    else:
        raise ValueError(f"Unsupported platform '{platform}'")

    validate_variant_content(platform, text)
    return text


def build_variants_for_post(
    title: str | None,
    stored_content: str,
    platforms: list[str] | None = None,
) -> dict[str, str]:
    target_platforms = platforms or ["telegram", "mock_x"]
    if len(set(target_platforms)) < 2:
        raise ValueError("broken rule [min_platforms]: select at least two distinct platforms")

    return {
        platform: generate_variant_text(platform, title, stored_content)
        for platform in target_platforms
    }