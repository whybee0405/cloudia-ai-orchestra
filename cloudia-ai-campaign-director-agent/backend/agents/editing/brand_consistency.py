"""Brand Consistency Agent — final check on every asset before human approval gate."""
import logging
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign, BrandGuidelines
from backend.ai import claude
from backend.ai.prompts.brand_consistency import BRAND_TONE_CHECK_PROMPT
from backend.config import PLATFORM_SPECS

logger = logging.getLogger(__name__)


class BrandConsistencyAgent(BaseAgent):
    name = "brand_consistency"

    def run(self, asset_id: int) -> dict:
        asset = self.db.get(ContentAsset, asset_id)
        if not asset:
            raise AgentError(f"Asset {asset_id} not found")

        campaign = self.db.get(Campaign, asset.campaign_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=asset.client_id).first()

        self._start_task(campaign.id, None, {"asset_id": asset_id}, pipeline_order=25)

        issues = []

        if asset.asset_type == "text":
            issues.extend(self._check_text(asset, guidelines, campaign))
        elif asset.asset_type == "image":
            issues.extend(self._check_image(asset, guidelines))
        elif asset.asset_type == "video":
            issues.extend(self._check_video(asset, guidelines))

        has_critical_or_high = any(i["severity"] in ("CRITICAL", "HIGH") for i in issues)
        passed = not has_critical_or_high

        asset.brand_check_passed = passed
        asset.brand_check_notes = "; ".join(f"[{i['severity']}] {i['issue']}" for i in issues) if issues else None
        asset.status = "approved_for_review" if passed else "brand_check_failed"
        self.db.commit()

        self._complete_task({"passed": passed, "issues": issues})
        return {"asset_id": asset_id, "passed": passed, "issues": issues}

    def _check_text(self, asset: ContentAsset, guidelines, campaign) -> list[dict]:
        issues = []
        text = asset.text_content or ""
        g = guidelines

        # Forbidden words
        for word in (g.forbidden_words or [] if g else []):
            if word.lower() in text.lower():
                issues.append({"field": "text_content", "issue": f"Forbidden word: {word!r}", "severity": "HIGH"})

        # Competitor names
        for name in (g.competitor_names or [] if g else []):
            if name.lower() in text.lower():
                issues.append({"field": "text_content", "issue": f"Competitor name: {name!r}", "severity": "CRITICAL"})

        # Required hashtags
        required = (g.required_elements or {}).get("hashtags_required", []) if g else []
        for tag in required + (campaign.campaign_hashtags or []):
            if tag.lower() not in text.lower():
                issues.append({"field": "text_content", "issue": f"Missing hashtag: {tag}", "severity": "HIGH"})

        # Character limit per platform
        platform_versions = asset.platform_versions or {}
        for platform, ver_data in platform_versions.items():
            cap = (ver_data.get("caption") or "") if isinstance(ver_data, dict) else ""
            limit = PLATFORM_SPECS.get(platform, {}).get("caption_max_chars", 99999)
            if cap and len(cap) > limit:
                issues.append({"field": f"{platform}_caption", "issue": f"Over char limit ({len(cap)}/{limit})", "severity": "HIGH"})

        # CTA check
        if g and (g.required_elements or {}).get("cta_required") and not any(
            kw in text.lower() for kw in ["learn more", "shop now", "get quote", "contact us", "book now", "find out"]
        ):
            issues.append({"field": "text_content", "issue": "CTA missing", "severity": "MEDIUM"})

        # Tone check via Claude
        if g and g.tone_keywords:
            tone_result, inp, out, cost = claude.call_json(
                system_prompt="You are a brand tone auditor.",
                user_prompt=BRAND_TONE_CHECK_PROMPT.format(
                    tone_keywords=", ".join(g.tone_keywords),
                    forbidden_words=", ".join(g.forbidden_words or []),
                    competitor_names=", ".join(g.competitor_names or []),
                    text=text[:1000],
                ),
            )
            self._track_tokens(inp, out, cost)
            issues.extend(tone_result.get("issues", []))

        return issues

    def _check_image(self, asset: ContentAsset, guidelines) -> list[dict]:
        issues = []
        if not guidelines:
            return issues
        if (guidelines.required_elements or {}).get("logo_on_all_images"):
            if not asset.platform_versions:
                issues.append({"field": "image", "issue": "No platform versions — logo overlay not confirmed", "severity": "HIGH"})
        return issues

    def _check_video(self, asset: ContentAsset, guidelines) -> list[dict]:
        issues = []
        script = asset.text_content or ""
        if not guidelines:
            return issues
        for name in (guidelines.competitor_names or []):
            if name.lower() in script.lower():
                issues.append({"field": "voiceover_script", "issue": f"Competitor name in script: {name!r}", "severity": "CRITICAL"})
        if not asset.platform_versions:
            issues.append({"field": "video", "issue": "No platform versions — brand outro not confirmed", "severity": "HIGH"})
        return issues
