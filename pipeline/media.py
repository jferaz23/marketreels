"""Optional stock-video backgrounds from Pexels (free API key: https://www.pexels.com/api/).

Without PEXELS_API_KEY every reel keeps its animated gradient (or the news photo), so this is purely cosmetic.
"""
import hashlib
import logging
import os

import requests

log = logging.getLogger(__name__)

DEFAULT_QUERIES = {
    "markets": "stock market trading screen",
    "macro": "city skyline night",
    "news": "newspaper business",
    "ideas": "modern office technology",
}


class Media:
    def __init__(self):
        self.key = os.environ.get("PEXELS_API_KEY", "").strip()
        self.cache = {}

    @property
    def enabled(self):
        return bool(self.key)

    def _videos(self, query):
        if query in self.cache:
            return self.cache[query]
        out = []
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                             params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 12},
                             headers={"Authorization": self.key}, timeout=20)
            r.raise_for_status()
            for v in r.json().get("videos", []):
                files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
                portrait = [f for f in files if f["height"] > f["width"] and 540 <= f["width"] <= 1080]
                if not portrait or v.get("duration", 0) < 6:
                    continue
                f = min(portrait, key=lambda f: abs(f["width"] - 720))
                out.append({"type": "video", "src": f["link"], "poster": v.get("image"),
                            "credit": f"Video: {v.get('user', {}).get('name', 'Pexels')} / Pexels"})
        except Exception as e:
            log.warning("pexels search '%s' failed: %s", query, e)
        self.cache[query] = out
        return out

    def background(self, reel_id, query):
        """Pick a stable video for a reel (same id -> same clip), or None."""
        if not self.enabled or not query:
            return None
        vids = self._videos(query)
        if not vids:
            return None
        i = int(hashlib.md5(reel_id.encode()).hexdigest(), 16) % len(vids)
        return vids[i]

    def decorate(self, reels):
        if not self.enabled:
            return
        for r in reels:
            if r.get("bg", {}).get("type") in ("video", "image"):
                continue
            bg = self.background(r["id"], r.pop("media_query", None) or DEFAULT_QUERIES.get(r["category"]))
            if bg:
                r["bg"] = bg
