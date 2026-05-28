"""
Context builder for CloudIA agent prompts.

Builds a structured, injection-safe context string from Client + Project
DB records. All client-supplied text fields are wrapped in <<< >>> delimiters
to contain any prompt injection attempts.

Usage:
    context = build_project_context(client, project)
    # Inject into every Claude prompt as part of the system or user message.
"""

import json
import structlog

log = structlog.get_logger()

MAX_FIELD_LENGTH = 500  # chars — truncate long fields with note

# Rough token estimate: 4 chars ≈ 1 token
_MAX_CONTEXT_CHARS = 4000 * 4  # 16 000 chars


def _safe_field(
    value: object,
    default: str = "Not provided",
    max_len: int = MAX_FIELD_LENGTH,
) -> str:
    """Return value as string, truncated if needed, or default if None/empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + f"... [truncated — original length {len(s)} chars]"
    return s


def _safe_json(value: object, default: str = "Not specified") -> str:
    """Safely serialise a JSON-able value to a pretty string."""
    if not value:
        return default
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return f"[Malformed JSON: {value[:100]}]"
    try:
        return json.dumps(value, indent=2)
    except (TypeError, ValueError):
        return f"[Non-serialisable value: {str(value)[:100]}]"


def _wrap(field_name: str, value: str) -> str:
    """Wrap a client-supplied field with injection-containment delimiters."""
    return f"<<<{field_name}>>>\n{value}\n<<</{field_name}>>>"


def build_project_context(client: object, project: object) -> str:
    """Build the full context string injected into every Claude prompt.

    Uses explicit delimiters around all client-supplied fields to prevent
    prompt injection via client data.

    Args:
        client: A Client ORM instance.
        project: A Project ORM instance.

    Returns:
        A multi-section string suitable for inclusion in a Claude system
        or user message.
    """

    # ------------------------------------------------------------------
    # CLIENT BRIEF
    # ------------------------------------------------------------------
    client_brief_lines = [
        "## CLIENT BRIEF",
        "",
        _wrap("business_name", _safe_field(getattr(client, "name", None))),
        _wrap("industry", _safe_field(getattr(client, "industry", None))),
        _wrap("business_type", _safe_field(getattr(client, "business_type", None))),
        _wrap(
            "target_audience",
            _safe_field(getattr(client, "target_audience", None)),
        ),
        _wrap("usp", _safe_field(getattr(client, "usp", None))),
        _wrap(
            "tone_of_voice",
            _safe_field(getattr(client, "tone_of_voice", None)),
        ),
        _wrap(
            "brand_colours",
            _safe_json(getattr(client, "brand_colours", None)),
        ),
        _wrap(
            "brand_fonts",
            _safe_json(getattr(client, "brand_fonts", None)),
        ),
        _wrap("city", _safe_field(getattr(client, "city", None))),
        _wrap("country", _safe_field(getattr(client, "country", None), default="South Africa")),
        _wrap(
            "contact_email",
            _safe_field(getattr(client, "contact_email", None)),
        ),
        _wrap(
            "contact_phone",
            _safe_field(getattr(client, "contact_phone", None)),
        ),
        _wrap("address", _safe_field(getattr(client, "address", None))),
        _wrap(
            "existing_website",
            _safe_field(getattr(client, "website_url", None)),
        ),
        _wrap(
            "social_links",
            _safe_json(getattr(client, "social_links", None)),
        ),
    ]

    # ------------------------------------------------------------------
    # PROJECT BRIEF
    # ------------------------------------------------------------------
    project_brief_raw = getattr(project, "brief", None)
    project_brief_str = _safe_json(project_brief_raw)

    project_brief_lines = [
        "",
        "## PROJECT BRIEF",
        "",
        _wrap("platform", _safe_field(getattr(project, "platform", None))),
        _wrap("project_brief_json", project_brief_str),
    ]

    # Pipeline plan (non-client-supplied — safe to include without delimiters)
    pipeline_plan_raw = getattr(project, "pipeline_plan", None)
    if pipeline_plan_raw:
        pipeline_plan_str = _safe_json(pipeline_plan_raw)
        project_brief_lines += [
            "",
            "### Pipeline Plan (system-generated — not client input)",
            pipeline_plan_str,
        ]

    # ------------------------------------------------------------------
    # YOUR ROLE
    # ------------------------------------------------------------------
    role_lines = [
        "",
        "## YOUR ROLE",
        "",
        "You are a senior web copywriter and digital strategist working for CloudIA,",
        "a South African digital agency. You are building a professional website for",
        "this specific client. All content must:",
        "1. Reflect the client's tone of voice exactly",
        "2. Speak directly to their stated target audience",
        "3. Be written for a South African market unless brief says otherwise",
        "4. Never use generic filler copy — every sentence earns its place",
        "5. Be factually grounded in the brief — do not invent services, products, or claims",
        "6. Where asked for JSON output: return ONLY valid JSON, no markdown, no preamble",
    ]

    # ------------------------------------------------------------------
    # Assemble and validate length
    # ------------------------------------------------------------------
    all_lines = client_brief_lines + project_brief_lines + role_lines
    context = "\n".join(all_lines)

    if len(context) > _MAX_CONTEXT_CHARS:
        log.warning(
            "context_exceeds_token_limit",
            chars=len(context),
            limit=_MAX_CONTEXT_CHARS,
            client_id=getattr(client, "id", None),
            project_id=getattr(project, "id", None),
        )

    brand_dna_client_id = getattr(client, "brand_dna_client_id", None)
    if brand_dna_client_id:
        try:
            from backend.utils.brand_dna import get_brand_context_block
            block = get_brand_context_block(str(brand_dna_client_id))
            if block:
                context = block + "\n\n" + context
        except Exception:
            pass

    return context
