import os
import json
import sqlite3
import logging
import uuid
import random
from typing import List, Dict, Any, Optional

import numpy as np

try:
    import openai
except Exception:  # pragma: no cover - openai may not be installed
    openai = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default styles if AI generation fails
DEFAULT_COLORS = [
    "#4CAF50", "#E91E63", "#FF9800", "#9C27B0",
    "#2196F3", "#607D8B", "#F44336", "#3F51B5"
]
DEFAULT_ICONS = ["🥛", "🏃", "💃", "👨‍🍳", "😂", "🎨", "🔬", "🤘"]


class MilkMobClassifier:
    """Dynamic classifier that groups videos into Milk Mobs."""

    def __init__(self, db_path: str = "milk_mobs.db", openai_api_key: Optional[str] = None,
                 similarity_threshold: float = 0.6) -> None:
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if self.openai_api_key and openai:
            openai.api_key = self.openai_api_key
        self._initialize_db()

    # ------------------------------------------------------------------
    # Database setup
    # ------------------------------------------------------------------
    def _initialize_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS mobs(
                    mob_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    color_theme TEXT,
                    icon TEXT,
                    centroid TEXT,
                    video_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS videos(
                    video_id TEXT PRIMARY KEY,
                    mob_id TEXT,
                    title TEXT,
                    description TEXT,
                    thumbnail_path TEXT,
                    video_path TEXT,
                    embedding TEXT,
                    location TEXT,
                    match_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(mob_id) REFERENCES mobs(mob_id)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def classify_video(self, analysis_results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Classify a video using its embedding. Create a new mob if necessary."""
        embedding = np.array(analysis_results.get("embedding", []), dtype=float)
        features = self._extract_features(analysis_results)

        mobs = self._load_mobs()
        best_id = None
        best_score = -1.0
        for mob in mobs:
            centroid = np.array(json.loads(mob["centroid"]), dtype=float)
            score = self._cosine_similarity(embedding, centroid)
            if score > best_score:
                best_score = score
                best_id = mob["mob_id"]

        if best_score < self.similarity_threshold or not mobs:
            best_id = self._create_mob_with_ai(features, embedding)
            best_score = 1.0

        mob_info = self._get_mob(best_id)
        if mob_info:
            self._store_video(best_id, analysis_results, metadata, embedding, best_score)
        return {**mob_info, "match_score": float(best_score)}

    def get_all_mobs(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                "SELECT mob_id, name, description, color_theme, icon, video_count FROM mobs ORDER BY video_count DESC"
            )
            rows = c.fetchall()
            return [
                {
                    "mob_id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "color_theme": r[3],
                    "icon": r[4],
                    "video_count": r[5],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_mob_videos(self, mob_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                """SELECT video_id, title, description, thumbnail_path, video_path, location, match_score
                   FROM videos WHERE mob_id=? ORDER BY match_score DESC LIMIT ?""",
                (mob_id, limit),
            )
            rows = c.fetchall()
            return [
                {
                    "video_id": r[0],
                    "title": r[1],
                    "description": r[2],
                    "thumbnail_path": r[3],
                    "video_path": r[4],
                    "location": r[5],
                    "match_score": r[6],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_mob_stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM videos")
            total_videos = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mobs")
            total_mobs = c.fetchone()[0]
            return {"total_videos": total_videos, "total_mobs": total_mobs}
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_mobs(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute("SELECT mob_id, centroid FROM mobs")
            rows = c.fetchall()
            return [{"mob_id": r[0], "centroid": r[1]} for r in rows]
        finally:
            conn.close()

    def _get_mob(self, mob_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                "SELECT mob_id, name, description, color_theme, icon, video_count FROM mobs WHERE mob_id=?",
                (mob_id,),
            )
            r = c.fetchone()
            if not r:
                return None
            return {
                "mob_id": r[0],
                "mob_name": r[1],
                "mob_description": r[2],
                "color_theme": r[3],
                "icon": r[4],
                "video_count": r[5],
            }
        finally:
            conn.close()

    def _store_video(self, mob_id: str, analysis_results: Dict[str, Any], metadata: Optional[Dict[str, Any]],
                      embedding: np.ndarray, score: float) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            video_id = analysis_results.get("video_id") or str(uuid.uuid4())
            title = metadata.get("post_data", {}).get("caption", "Video") if metadata else "Video"
            description = metadata.get("post_data", {}).get("caption", "") if metadata else ""
            thumbnail = metadata.get("thumbnail_path") if metadata else None
            video_path = metadata.get("video_path") if metadata else None
            location = metadata.get("post_data", {}).get("location", {}).get("place_name") if metadata else None

            c.execute(
                """INSERT OR REPLACE INTO videos
                       (video_id, mob_id, title, description, thumbnail_path, video_path,
                        embedding, location, match_score)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    video_id,
                    mob_id,
                    title,
                    description,
                    thumbnail,
                    video_path,
                    json.dumps(embedding.tolist()),
                    location,
                    score,
                ),
            )
            c.execute("SELECT centroid, video_count FROM mobs WHERE mob_id=?", (mob_id,))
            cent, count = c.fetchone()
            old_centroid = np.array(json.loads(cent), dtype=float)
            new_centroid = (old_centroid * count + embedding) / (count + 1)
            c.execute(
                "UPDATE mobs SET centroid=?, video_count=video_count+1, last_updated=CURRENT_TIMESTAMP WHERE mob_id=?",
                (json.dumps(new_centroid.tolist()), mob_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _create_mob_with_ai(self, features: List[str], embedding: np.ndarray) -> str:
        mob_id = f"mob_{uuid.uuid4().hex[:8]}"
        name = f"Milk Mob {mob_id[-4:]}"
        description = "A community for unique milk moments."
        if self.openai_api_key and openai:
            try:
                prompt = (
                    "Create a short name and description for a community of videos that share these features: "
                    + ", ".join(features[:10])
                )
                resp = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                )
                text = resp.choices[0].message.content
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if lines:
                    name = lines[0][:40]
                if len(lines) > 1:
                    description = lines[1]
            except Exception as e:  # pragma: no cover - network not available
                logger.warning("OpenAI generation failed: %s", e)
        color = random.choice(DEFAULT_COLORS)
        icon = random.choice(DEFAULT_ICONS)
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO mobs(mob_id, name, description, color_theme, icon, centroid) VALUES (?, ?, ?, ?, ?, ?)",
                (mob_id, name, description, color, icon, json.dumps(embedding.tolist())),
            )
            conn.commit()
        finally:
            conn.close()
        return mob_id

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        if a.size == 0 or b.size == 0:
            return 0.0
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _extract_features(self, analysis_results: Dict[str, Any]) -> List[str]:
        features: List[str] = []
        for key in ("objects", "actions"):
            if key in analysis_results:
                features.extend([str(x).lower() for x in analysis_results[key]])
        for key in ("description", "semantic_analysis"):
            if key in analysis_results and isinstance(analysis_results[key], str):
                features.extend(self._extract_keywords(analysis_results[key]))
        for mention in analysis_results.get("audio_mentions", []):
            features.extend(self._extract_keywords(mention))
        uniq: List[str] = []
        seen: set[str] = set()
        for f in features:
            if f not in seen:
                uniq.append(f)
                seen.add(f)
        return uniq

    def _extract_keywords(self, text: str) -> List[str]:
        common = {
            "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "with",
            "for", "at", "by", "is", "are", "was", "were", "be", "has", "have", "had",
        }
        return [w for w in text.lower().split() if len(w) > 2 and w not in common]
