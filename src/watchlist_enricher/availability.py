"""Turn service/country offers into the parenthesis Jorge asked for.

Netflix wins over Prime Video. Spain hides the country name. Anywhere else,
the country is the best one in Jorge's priority list. RTVE Play is only a
fallback, and only from the free / ad-supported section.
"""

from watchlist_enricher.countries import best_country, canonicalize_country
from watchlist_enricher.models import Offer
from watchlist_enricher.textutil import fold_title


def service_kind(name: str) -> str | None:
    """Classify a service name. Anything else is ignored in v1."""

    folded = fold_title(name)
    if folded == "netflix" or folded.startswith("netflix "):
        return "netflix"
    if folded in {"prime video", "amazon prime video", "amazon prime"} or folded.startswith("prime video"):
        return "prime"
    if folded in {"rtve play", "rtve"}:
        return "rtve"
    return None


def canonical_service_name(name: str) -> str:
    kind = service_kind(name)
    if kind == "netflix":
        return "Netflix"
    if kind == "prime":
        return "Prime Video"
    if kind == "rtve":
        return "RTVE Play"
    return name.strip()


def normalize_section(value: str) -> str:
    folded = fold_title(value)
    if folded in {"free", "ads", "ad supported", "free with ads", "avod", "gratis"} or "ad supported" in folded:
        return "free"
    if folded in {"dump", "other", "logo", "logos", "other services"} or "other streaming" in folded:
        return "dump"
    return "catalog"


def _catalog_countries(offers: list[Offer], kind: str) -> list[str]:
    found: list[str] = []
    for offer in offers:
        if offer.section != "catalog":
            continue
        if service_kind(offer.service) != kind:
            continue
        for country in offer.countries:
            canonical = canonicalize_country(country)
            if canonical and canonical not in found:
                found.append(canonical)
    return found


def _has_rtve_free(offers: list[Offer]) -> bool:
    return any(offer.section == "free" and service_kind(offer.service) == "rtve" for offer in offers)


def format_availability(offers: list[Offer]) -> str | None:
    """Return the text inside the parentheses, or None to leave the title bare.

    Order, confirmed with Jorge:
    Netflix in Spain, else Prime Video in Spain, else Netflix elsewhere,
    else Prime Video elsewhere, else RTVE Play in the free section, else nothing.
    """

    netflix = _catalog_countries(offers, "netflix")
    prime = _catalog_countries(offers, "prime")
    if "España" in netflix:
        return "Netflix"
    if "España" in prime:
        return "Prime Video"
    if netflix:
        return f"Netflix, {best_country(netflix)}"
    if prime:
        return f"Prime Video, {best_country(prime)}"
    if _has_rtve_free(offers):
        return "RTVE Play"
    return None
