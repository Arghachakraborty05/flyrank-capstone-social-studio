import re
from dataclasses import dataclass


class ConstraintViolationError(ValueError):
    """Raised when content breaks a platform constraint profile."""


@dataclass(frozen=True)
class PlatformConstraintProfile:
    platform: str
    max_length: int
    max_hashtags: int
    required_tone: str
    require_prompt_or_question: bool = False


PLATFORM_PROFILES: dict[str, PlatformConstraintProfile] = {
    "telegram": PlatformConstraintProfile(
        platform="telegram",
        max_length=4096,
        max_hashtags=5,
        required_tone="informative",
        require_prompt_or_question=False,
    ),
    "mock_x": PlatformConstraintProfile(
        platform="mock_x",
        max_length=280,
        max_hashtags=3,
        required_tone="concise",
        require_prompt_or_question=False,
    ),
    "mock_linkedin": PlatformConstraintProfile(
        platform="mock_linkedin",
        max_length=3000,
        max_hashtags=5,
        required_tone="professional",
        require_prompt_or_question=True,
    ),
}


def count_hashtags(content: str) -> int:
    return len(re.findall(r"(?<!\w)#[A-Za-z0-9_]+", content))


def check_tone_rule(profile: PlatformConstraintProfile, content: str) -> str | None:
    cleaned = content.strip()
    if not cleaned:
        return f"tone ({profile.required_tone}): content cannot be empty"

    if profile.platform == "mock_x":
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        if len(paragraphs) > 2:
            return f"tone ({profile.required_tone}): X variant must not exceed 2 paragraphs"

    if profile.platform == "mock_linkedin" and profile.require_prompt_or_question:
        has_question_or_prompt = ("?" in cleaned) or bool(
            re.search(
                r"\b(thoughts|share|comment|how do you|what do you think)\b",
                cleaned,
                re.IGNORECASE,
            )
        )
        if not has_question_or_prompt:
            return f"tone ({profile.required_tone}): LinkedIn variant must include a question or discussion prompt"

    return None


def validate_variant_content(platform: str, content: str) -> None:
    profile = PLATFORM_PROFILES.get(platform)
    if profile is None:
        raise ConstraintViolationError(f"Broken rule [platform_profile]: unsupported platform '{platform}'")

    violations: list[str] = []

    if len(content) > profile.max_length:
        violations.append(
            f"max_length ({len(content)} > {profile.max_length} for {platform})"
        )

    hashtag_count = count_hashtags(content)
    if hashtag_count > profile.max_hashtags:
        violations.append(
            f"max_hashtags ({hashtag_count} > {profile.max_hashtags} for {platform})"
        )

    tone_error = check_tone_rule(profile, content)
    if tone_error:
        violations.append(tone_error)

    if violations:
        raise ConstraintViolationError(
            f"Blocked variant for '{platform}' — broken rule(s): " + "; ".join(violations)
        )