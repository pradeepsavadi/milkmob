import logging
import numpy as np
from collections import Counter, defaultdict
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MilkMobClassifier:
    """
    Classifies valid videos into thematic "Milk Mobs"
    """
    def __init__(self, db_path="milk_mobs.db", n_clusters=7):
        """
        Initialize the Milk Mob classifier
        
        Parameters:
        db_path (str): Path to SQLite database for caching
        n_clusters (int): Number of clusters to create if model doesn't exist
        """
        self.n_clusters = n_clusters
        self.db_path = db_path
        
        # Initialize the database for caching
        self._initialize_db()
        
        # Define starter mob data (will be updated based on clusters)
        self.mobs = {
            "active_milk_mob": {
                "name": "Active Milk Mob",
                "description": "Sports and fitness enthusiasts enjoying milk",
                "keywords": [
                    "sports", "exercise", "workout", "fitness", "gym", "athlete", 
                    "running", "jumping", "training", "outdoor", "active"
                ]
            },
            "dance_milk_mob": {
                "name": "Dance Milk Mob",
                "description": "Creative dancers incorporating milk",
                "keywords": [
                    "dance", "dancing", "choreography", "music", "rhythm", 
                    "performance", "routine", "moves", "dancer", "stage"
                ]
            },
            "chef_milk_mob": {
                "name": "Chef Milk Mob",
                "description": "Culinary creations featuring milk",
                "keywords": [
                    "cooking", "baking", "recipe", "chef", "kitchen", "food", 
                    "culinary", "ingredients", "meal", "dish", "restaurant"
                ]
            },
            "comedy_milk_mob": {
                "name": "Comedy Milk Mob",
                "description": "Humorous and entertaining milk moments",
                "keywords": [
                    "funny", "comedy", "joke", "laugh", "humor", "prank", 
                    "entertaining", "laughter", "silly", "amusing", "comedic"
                ]
            },
            "art_milk_mob": {
                "name": "Art Milk Mob",
                "description": "Artistic expressions with milk",
                "keywords": [
                    "art", "painting", "creative", "artistic", "design", "craft", 
                    "creation", "colors", "sculpture", "visual", "drawing"
                ]
            },
            "science_milk_mob": {
                "name": "Science Milk Mob",
                "description": "Scientific experiments and discoveries with milk",
                "keywords": [
                    "science", "experiment", "laboratory", "discovery", "research", 
                    "chemistry", "physics", "reaction", "testing", "analysis"
                ]
            },
            "extreme_milk_mob": {
                "name": "Extreme Milk Mob",
                "description": "Adventurous and daring milk challenges",
                "keywords": [
                    "extreme", "challenge", "adventure", "daring", "stunt", 
                    "dangerous", "risky", "impressive", "thrilling", "exciting"
                ]
            }
        }
    
    def _initialize_db(self):
        """Initialize SQLite database for caching cluster data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mobs (
                mob_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                cluster_id INTEGER,
                video_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                mob_id TEXT,
                title TEXT,
                location TEXT,
                match_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mob_id) REFERENCES mobs(mob_id)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mob_keywords (
                mob_id TEXT,
                keyword TEXT,
                weight REAL,
                PRIMARY KEY (mob_id, keyword),
                FOREIGN KEY (mob_id) REFERENCES mobs(mob_id)
            )
            ''')
            
            # Initialize with default mobs if table is empty
            cursor.execute("SELECT COUNT(*) FROM mobs")
            if cursor.fetchone()[0] == 0:
                for mob_id, mob_data in self.mobs.items():
                    cursor.execute(
                        "INSERT INTO mobs (mob_id, name, description, cluster_id) VALUES (?, ?, ?, ?)",
                        (mob_id, mob_data["name"], mob_data["description"], -1)
                    )
                    
                    for keyword in mob_data["keywords"]:
                        cursor.execute(
                            "INSERT INTO mob_keywords (mob_id, keyword, weight) VALUES (?, ?, ?)",
                            (mob_id, keyword, 1.0)
                        )
            
            conn.commit()
            conn.close()
            logger.info("Database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
    def classify_video(self, analysis_results, location=None):
        """
        Assign video to appropriate milk mob based on content
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        location (dict): Location data if available
        
        Returns:
        dict: Mob assignment information
        """
        logger.info("Classifying video into Milk Mob")
        
        try:
            # Extract features from analysis results
            features = self._extract_features(analysis_results)
            
            # Calculate match score for each mob
            mob_scores = {}
            for mob_id, mob_data in self.mobs.items():
                mob_scores[mob_id] = self._calculate_mob_match(features, mob_data)
                logger.info(f"Match score for {mob_id}: {mob_scores[mob_id]}")
            
            # Select best matching mob
            best_mob = max(mob_scores.items(), key=lambda x: x[1])
            
            # Secondary mob (second highest score)
            remaining_mobs = {k: v for k, v in mob_scores.items() if k != best_mob[0]}
            secondary_mob = max(remaining_mobs.items(), key=lambda x: x[1]) if remaining_mobs else None
            
            # Get mob data from database
            mob_assignment = self._get_mob_data(best_mob[0])
            
            if not mob_assignment:
                # Fallback to static mob data
                mob_assignment = {
                    "mob_id": best_mob[0],
                    "mob_name": self.mobs[best_mob[0]]["name"],
                    "mob_description": self.mobs[best_mob[0]]["description"],
                    "keywords": self.mobs[best_mob[0]]["keywords"][:5],
                    "match_score": best_mob[1]
                }
            else:
                mob_assignment["match_score"] = best_mob[1]
            
            # Add secondary mob info
            if secondary_mob:
                secondary_mob_data = self._get_mob_data(secondary_mob[0]) or {
                    "mob_id": secondary_mob[0],
                    "mob_name": self.mobs[secondary_mob[0]]["name"],
                    "match_score": secondary_mob[1]
                }
                
                mob_assignment["secondary_mob"] = {
                    "mob_id": secondary_mob_data["mob_id"],
                    "mob_name": secondary_mob_data["mob_name"],
                    "match_score": secondary_mob[1]
                }
            
            # Add feature breakdown
            mob_assignment["feature_breakdown"] = self._get_feature_breakdown(features)
            
            # Find nearby mobs if location provided
            if location:
                nearby_mobs = self._find_nearby_mobs(location)
                if nearby_mobs:
                    mob_assignment["nearby_mobs"] = nearby_mobs
            
            # Cache the assignment
            self._cache_assignment(
                analysis_results.get("video_id", "unknown_video"), 
                mob_assignment, 
                location
            )
            
            logger.info(f"Video classified into {mob_assignment['mob_name']}")
            return mob_assignment
            
        except Exception as e:
            logger.error(f"Error classifying video: {str(e)}")
            # Default to Active Milk Mob if classification fails
            return {
                "mob_id": "active_milk_mob",
                "mob_name": self.mobs["active_milk_mob"]["name"],
                "mob_description": self.mobs["active_milk_mob"]["description"],
                "match_score": 0.5,
                "error": str(e)
            }
    
    def _extract_features(self, analysis_results):
        """
        Extract relevant features from analysis results
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        
        Returns:
        list: Extracted features as strings
        """
        features = []
        
        # Add detected objects
        if "objects" in analysis_results:
            features.extend([obj.lower() for obj in analysis_results["objects"]])
        
        # Add detected actions
        if "actions" in analysis_results:
            features.extend([action.lower() for action in analysis_results["actions"]])
        
        # Add audio mentions
        if "audio_mentions" in analysis_results:
            for mention in analysis_results["audio_mentions"]:
                words = self._extract_keywords_from_text(mention)
                features.extend(words)
        
        # Extract keywords from scenes and descriptions
        if "description" in analysis_results:
            words = self._extract_keywords_from_text(analysis_results["description"])
            features.extend(words)
            
        if "semantic_analysis" in analysis_results:
            words = self._extract_keywords_from_text(analysis_results["semantic_analysis"])
            features.extend(words)
        
        # Remove duplicates while preserving order (to maintain prominence)
        unique_features = []
        seen = set()
        for feature in features:
            if feature not in seen:
                seen.add(feature)
                unique_features.append(feature)
        
        return unique_features
    
    def _extract_keywords_from_text(self, text):
        """
        Extract keywords from text, filtering out common words
        
        Parameters:
        text (str): Text to extract keywords from
        
        Returns:
        list: Extracted keywords
        """
        # Common words to filter out
        common_words = set([
            "the", "a", "an", "and", "or", "but", "of", "to", "in", "on",
            "with", "for", "at", "by", "as", "is", "are", "was", "were", 
            "be", "being", "been", "have", "has", "had", "do", "does", 
            "did", "will", "would", "shall", "should", "can", "could",
            "may", "might", "must", "that", "this", "these", "those",
            "it", "its", "they", "them", "their", "he", "him", "his",
            "she", "her", "we", "us", "our", "you", "your"
        ])
        
        # Convert to lowercase and split into words
        if not isinstance(text, str):
            return []
            
        words = text.lower().split()
        
        # Filter out common words and short words
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        
        return keywords
    
    def _calculate_mob_match(self, features, mob_data):
        """
        Calculate match score between video features and mob category
        
        Parameters:
        features (list): Features extracted from the video
        mob_data (dict): Mob category data with keywords
        
        Returns:
        float: Match score between 0 and 1
        """
        if not features:
            return 0.0
            
        keywords = mob_data["keywords"]
        
        # Count matching keywords
        matches = 0
        max_potential_matches = min(len(keywords), len(features))
        
        # Weight earlier features more (they are more prominent in the video)
        feature_weights = {feature: 1.0 / (i + 1) for i, feature in enumerate(features)}
        
        # Search for keywords in features
        for keyword in keywords:
            for feature in features:
                if keyword.lower() in feature:
                    matches += feature_weights[feature]
                    break
        
        # Calculate normalized score
        if max_potential_matches > 0:
            return matches / max_potential_matches
        return 0.0
    
    def _get_feature_breakdown(self, features):
        """
        Get breakdown of extracted features for explanation
        
        Parameters:
        features (list): Extracted features
        
        Returns:
        dict: Feature breakdown
        """
        # Count frequency of features
        feature_counts = Counter(features)
        
        # Sort by frequency
        sorted_features = feature_counts.most_common(10)
        
        return {
            "top_features": sorted_features,
            "feature_count": len(features),
            "unique_feature_count": len(feature_counts)
        }
    
    def _get_mob_data(self, mob_id):
        """
        Get mob data from database
        
        Parameters:
        mob_id (str): Mob ID
        
        Returns:
        dict: Mob data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get mob info
            cursor.execute(
                """
                SELECT name, description, video_count
                FROM mobs
                WHERE mob_id = ?
                """,
                (mob_id,)
            )
            
            row = cursor.fetchone()
            
            if not row:
                return None
                
            name, description, video_count = row
            
            # Get keywords
            cursor.execute(
                """
                SELECT keyword
                FROM mob_keywords
                WHERE mob_id = ?
                ORDER BY weight DESC
                LIMIT 10
                """,
                (mob_id,)
            )
            
            keywords = [keyword[0] for keyword in cursor.fetchall()]
            
            conn.close()
            
            return {
                "mob_id": mob_id,
                "mob_name": name,
                "mob_description": description,
                "video_count": video_count,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"Error getting mob data: {str(e)}")
            return None
    
    def _cache_assignment(self, video_id, mob_assignment, location=None):
        """
        Cache the mob assignment in the database
        
        Parameters:
        video_id (str): Video ID
        mob_assignment (dict): Mob assignment information
        location (dict): Location data if available
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            location_str = None
            if location and "place_name" in location:
                location_str = location["place_name"]
            
            # Insert video assignment
            cursor.execute(
                """
                INSERT OR REPLACE INTO videos 
                (video_id, mob_id, title, location, match_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    video_id, 
                    mob_assignment["mob_id"],
                    f"Video {video_id[:8]}", 
                    location_str,
                    mob_assignment["match_score"]
                )
            )
            
            # Update mob video count
            cursor.execute(
                """
                UPDATE mobs SET video_count = video_count + 1, 
                last_updated = CURRENT_TIMESTAMP
                WHERE mob_id = ?
                """,
                (mob_assignment["mob_id"],)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error caching assignment: {str(e)}")
    
    def _find_nearby_mobs(self, location, limit=3):
        """
        Find mobs near the given location
        
        Parameters:
        location (dict): Location data
        limit (int): Maximum number of nearby mobs to return
        
        Returns:
        list: Nearby mobs
        """
        nearby_mobs = []
        
        try:
            if not location or "place_name" not in location:
                return nearby_mobs
                
            place_name = location["place_name"]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find videos with the same location
            cursor.execute(
                """
                SELECT v.mob_id, m.name, m.description, COUNT(v.video_id) as video_count
                FROM videos v
                JOIN mobs m ON v.mob_id = m.mob_id
                WHERE v.location = ?
                GROUP BY v.mob_id
                ORDER BY video_count DESC
                LIMIT ?
                """,
                (place_name, limit)
            )
            
            rows = cursor.fetchall()
            
            for row in rows:
                mob_id, name, description, video_count = row
                
                nearby_mobs.append({
                    "mob_id": mob_id,
                    "name": name,
                    "description": description,
                    "location": place_name,
                    "video_count": video_count
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error finding nearby mobs: {str(e)}")
        
        return nearby_mobs
    
    def get_all_mobs(self):
        """
        Get information about all defined mobs
        
        Returns:
        list: Information about all mobs
        """
        try:
            # Check if database file exists and has been initialized
            if not os.path.exists(self.db_path):
                logger.warning(f"Database file {self.db_path} does not exist. Initializing database.")
                self._initialize_db()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT m.mob_id, m.name, m.description, m.video_count, m.cluster_id
                FROM mobs m
                ORDER BY m.video_count DESC
                """
            )
            
            rows = cursor.fetchall()
            
            mob_info = []
            
            for row in rows:
                mob_id, name, description, video_count, cluster_id = row
                
                # Get keywords for this mob
                cursor.execute(
                    """
                    SELECT keyword FROM mob_keywords 
                    WHERE mob_id = ? 
                    ORDER BY weight DESC LIMIT 5
                    """,
                    (mob_id,)
                )
                
                keywords = [keyword[0] for keyword in cursor.fetchall()]
                
                # Get sample videos
                cursor.execute(
                    """
                    SELECT video_id, title, location, match_score
                    FROM videos
                    WHERE mob_id = ?
                    ORDER BY match_score DESC
                    LIMIT 3
                    """,
                    (mob_id,)
                )
                
                sample_videos = []
                for video_row in cursor.fetchall():
                    video_id, title, location, match_score = video_row
                    sample_videos.append({
                        "video_id": video_id,
                        "title": title,
                        "location": location,
                        "match_score": match_score
                    })
                
                mob_info.append({
                    "mob_id": mob_id,
                    "name": name,
                    "description": description,
                    "video_count": video_count,
                    "cluster_id": cluster_id,
                    "sample_keywords": keywords,
                    "sample_videos": sample_videos
                })
            
            conn.close()
            
            # If we got no results from the database, use static mobs as fallback
            if not mob_info:
                logger.info("No mobs found in database, using static mobs as fallback")
                # Fallback to static mobs
                for mob_id, data in self.mobs.items():
                    mob_info.append({
                        "mob_id": mob_id,
                        "name": data["name"],
                        "description": data["description"],
                        "sample_keywords": data["keywords"][:5],
                        "video_count": 0,
                        "sample_videos": []
                    })
            
            return mob_info
            
        except Exception as e:
            logger.error(f"Error getting all mobs: {str(e)}")
            
            # Ensure we always return the static mobs even if database query fails
            logger.info("Using static mobs as fallback due to error")
            mob_info = []
            
            for mob_id, data in self.mobs.items():
                mob_info.append({
                    "mob_id": mob_id,
                    "name": data["name"],
                    "description": data["description"],
                    "sample_keywords": data["keywords"][:5],
                    "video_count": 0,
                    "sample_videos": []
                })
            
            return mob_info
    
    def get_mob_stats(self):
        """
        Get statistics about mobs
        
        Returns:
        dict: Mob statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get mob counts
            cursor.execute(
                """
                SELECT m.name, m.video_count
                FROM mobs m
                ORDER BY m.video_count DESC
                LIMIT 10
                """
            )
            
            mob_counts = [(name, count) for name, count in cursor.fetchall()]
            
            # Get location distribution
            cursor.execute(
                """
                SELECT location, COUNT(*) as count
                FROM videos
                WHERE location IS NOT NULL
                GROUP BY location
                ORDER BY count DESC
                LIMIT 10
                """
            )
            
            location_distribution = [(location or "Unknown", count) for location, count in cursor.fetchall()]
            
            # Get top videos
            cursor.execute(
                """
                SELECT v.video_id, v.title, v.match_score, m.name as mob_name
                FROM videos v
                JOIN mobs m ON v.mob_id = m.mob_id
                ORDER BY v.match_score DESC
                LIMIT 5
                """
            )
            
            top_videos = []
            for row in cursor.fetchall():
                video_id, title, match_score, mob_name = row
                top_videos.append({
                    "video_id": video_id,
                    "title": title,
                    "match_score": match_score,
                    "mob_name": mob_name
                })
            
            conn.close()
            
            return {
                "mob_counts": mob_counts,
                "location_distribution": location_distribution,
                "top_videos": top_videos,
                "total_videos": sum(count for _, count in mob_counts),
                "total_mobs": len(mob_counts)
            }
            
        except Exception as e:
            logger.error(f"Error getting mob stats: {str(e)}")
            return {
                "mob_counts": [],
                "location_distribution": [],
                "top_videos": [],
                "total_videos": 0,
                "total_mobs": 0,
                "error": str(e)
            }