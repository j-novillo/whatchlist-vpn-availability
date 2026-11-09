"""Stream with VPN lookup. Public HTML only; /api/ is refused."""

from watchlist_enricher.streamwithvpn.client import HttpCatalog
from watchlist_enricher.streamwithvpn.fixtures import FixtureCatalog

__all__ = ["HttpCatalog", "FixtureCatalog"]
