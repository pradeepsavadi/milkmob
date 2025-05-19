import os
import json
import logging
import sqlite3
from datetime import datetime
import numpy as np
from collections import Counter
import openai  # pip install openai

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MilkMobClassifier:
    """
    Classifier for segmenting videos into thematic Milk Mobs
    Using both Twelve Labs analysis and LLM interpretation
    """
    def __init__(self, db_path="milk_mobs.db", openai_api_key=None):
        """
        Initialize the Milk Mob classifier
        
        Parameters:
        db_path (str): Path to SQLite database
        openai_api_key (str): OpenAI API key for LLM analysis
        """
        self.db_path = db_path
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize OpenAI client if key is provided
        # Initialize OpenAI client if key is provided
        if self.openai_api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            except TypeError:
                # Fallback for older OpenAI package or proxy issues
                import openai as openai_module
                openai_module.api_key = self.openai_api_key
                self.openai_client = openai_module
                
        # Define enhanced mob data with color themes and icons
        self.mobs = {
            "active_milk_mob": {
                "name": "Active Milk Mob",
                "description": "Sports and fitness enthusiasts enjoying milk for recovery and performance",
                "color_theme": "#4CAF50",
                "icon": "🏃‍♀️",
                "keywords": [
                    "sports", "exercise", "workout", "fitness", "gym", "athlete", 
                    "running", "jumping", "training", "outdoor", "active"
                ]
            },
            "dance_milk_mob": {
                "name": "Dance Milk Mob",
                "description": "Creative dancers incorporating milk into their routines and performances",
                "color_theme": "#E91E63",
                "icon": "💃",
                "keywords": [
                    "dance", "dancing", "choreography", "music", "rhythm", 
                    "performance", "routine", "moves", "dancer", "stage"
                ]
            },
            "chef_milk_mob": {
                "name": "Chef Milk Mob",
                "description": "Culinary creations featuring milk as a star ingredient",
                "color_theme": "#FF9800",
                "icon": "👨‍🍳",
                "keywords": [
                    "cooking", "baking", "recipe", "chef", "kitchen", "food", 
                    "culinary", "ingredients", "meal", "dish", "restaurant"
                ]
            },
            "comedy_milk_mob": {
                "name": "Comedy Milk Mob",
                "description": "Humorous and entertaining milk moments that make you laugh",
                "color_theme": "#9C27B0",
                "icon": "😂",
                "keywords": [
                    "funny", "comedy", "joke", "laugh", "humor", "prank", 
                    "entertaining", "laughter", "silly", "amusing", "comedic"
                ]
            },
            "art_milk_mob": {
                "name": "Art Milk Mob",
                "description": "Artistic expressions using milk as a creative medium",
                "color_theme": "#2196F3",
                "icon": "🎨",
                "keywords": [
                    "art", "painting", "creative", "artistic", "design", "craft", 
                    "creation", "colors", "sculpture", "visual", "drawing"
                ]
            },
            "science_milk_mob": {
                "name": "Science Milk Mob",
                "description": "Scientific experiments and discoveries featuring milk properties",
                "color_theme": "#607D8B",
                "icon": "🔬",
                "keywords": [
                    "science", "experiment", "laboratory", "discovery", "research", 
                    "chemistry", "physics", "reaction", "testing", "analysis"
                ]
            },
            "extreme_milk_mob": {
                "name": "Extreme Milk Mob",
                "description": "Adventurous and daring milk challenges pushing the limits",
                "color_theme": "#F44336",
                "icon": "🤘",
                "keywords": [
                    "extreme", "challenge", "adventure", "daring", "stunt", 
                    "dangerous", "risky", "impressive", "thrilling", "exciting"
                ]
            }
        }
        
        # Initialize the database
        self._initialize_db()
        
    def _initialize_db(self):
        """Initialize enhanced database with additional fields"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enhanced mobs table with color theme and icon
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mobs (
                mob_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                color_theme TEXT,
                icon TEXT,
                cluster_id INTEGER,
                video_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Enhanced videos table with thumbnail and video_path
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                mob_id TEXT,
                title TEXT,
                description TEXT,
                thumbnail_path TEXT,
                video_path TEXT,
                location TEXT,
                match_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mob_id) REFERENCES mobs(mob_id)
            )
            ''')
            
            # Keep the keywords table
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
                        "INSERT INTO mobs (mob_id, name, description, color_theme, icon, cluster_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (mob_id, mob_data["name"], mob_data["description"], 
                         mob_data["color_theme"], mob_data["icon"], -1)
                    )
                    
                    for keyword in mob_data["keywords"]:
                        cursor.execute(
                            "INSERT INTO mob_keywords (mob_id, keyword, weight) VALUES (?, ?, ?)",
                            (mob_id, keyword, 1.0)
                        )
            
            conn.commit()
            conn.close()
            logger.info("Enhanced database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
    def classify_video(self, analysis_results, metadata):
        """
        Assign video to appropriate milk mob using enhanced classification
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        metadata (dict): Additional video metadata including paths and post_data
        
        Returns:
        dict: Mob assignment information
        """
        logger.info("Classifying video with enhanced classifier")

        try:
            features = self._extract_features(analysis_results)
            logger.info(f"Extracted features: {features}")

            is_food_prep = False
            is_cheese_making = False

            if metadata and 'validation' in metadata:
                validation = metadata['validation']
                is_food_prep = validation.get('is_food_prep', False)
                is_cheese_making = validation.get('is_cheese_making', False)
                suggested_mob = validation.get('mob_suggestion')
                if suggested_mob and suggested_mob in self.mobs:
                    logger.info(f"Using suggested mob from validation: {suggested_mob}")
                    best_mob = (suggested_mob, 0.8)
                    mob_assignment = self._get_mob_data(best_mob[0])
                    if mob_assignment:
                        mob_assignment["match_score"] = best_mob[1]
                        mob_assignment["explanation"] = "Your video shows features that match with cheese-making and culinary uses of milk."
                        self._cache_assignment(
                            analysis_results.get("video_id", "unknown_video"),
                            mob_assignment,
                            metadata,
                        )
                        return mob_assignment

            if is_food_prep or is_cheese_making:
                features.extend(["cooking", "food", "preparation", "recipe", "culinary"])
            if is_cheese_making:
                features.extend(["cheese", "dairy", "chef", "kitchen", "food"])

            llm_analysis = None
            if hasattr(self, 'openai_client'):
                try:
                    llm_analysis = self._analyze_with_llm(features, analysis_results)
                    logger.info(f"LLM analysis completed: {llm_analysis}")
                except Exception as e:
                    logger.warning(f"LLM analysis failed: {str(e)}")

            mob_scores = {}
            for mob_id, mob_data in self.mobs.items():
                mob_scores[mob_id] = self._calculate_mob_match(features, mob_data)
                logger.info(f"Match score for {mob_id}: {mob_scores[mob_id]}")
            
            # Final decision - combine LLM and traditional scores if LLM available
            if llm_analysis and 'primary_mob' in llm_analysis:
                # Use LLM's primary mob but adjust with traditional scores
                primary_mob = llm_analysis['primary_mob']
                # Boost traditional score with LLM confidence
                mob_scores[primary_mob] = max(
                    mob_scores[primary_mob],
                    llm_analysis.get('primary_confidence', 70) / 100
                )
                best_mob = (primary_mob, mob_scores[primary_mob])
            else:
                # Fallback to traditional scoring
                best_mob = max(mob_scores.items(), key=lambda x: x[1])

            if best_mob[1] == 0:
                if is_cheese_making:
                    best_mob = ("chef_milk_mob", 0.7)
                else:
                    semantic_text = analysis_results.get("semantic_analysis", "").lower()
                    if "cook" in semantic_text or "recipe" in semantic_text or "food" in semantic_text:
                        best_mob = ("chef_milk_mob", 0.6)
                    elif "art" in semantic_text or "creative" in semantic_text:
                        best_mob = ("art_milk_mob", 0.6)
                    elif "experiment" in semantic_text or "science" in semantic_text:
                        best_mob = ("science_milk_mob", 0.6)
                    elif "funny" in semantic_text or "laugh" in semantic_text:
                        best_mob = ("comedy_milk_mob", 0.6)
                    else:
                        best_mob = ("active_milk_mob", 0.5)
            
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
                    "color_theme": self.mobs[best_mob[0]]["color_theme"],
                    "icon": self.mobs[best_mob[0]]["icon"],
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
            
            # Add LLM explanation if available
            if llm_analysis and 'explanation' in llm_analysis:
                mob_assignment["explanation"] = llm_analysis['explanation']
            else:
                if is_cheese_making:
                    mob_assignment["explanation"] = "Your video shows cheese-making, which is a creative culinary use of milk!"
                elif is_food_prep:
                    mob_assignment["explanation"] = "Your video shows food preparation with milk-based ingredients!"
                else:
                    mob_assignment["explanation"] = f"Your video shows features that match with the {mob_assignment['mob_name']} theme."
            
            # Add feature breakdown
            mob_assignment["feature_breakdown"] = self._get_feature_breakdown(features)
            
            # Find nearby mobs if location provided
            location = None
            if metadata and 'post_data' in metadata and 'location' in metadata['post_data']:
                location = metadata['post_data']['location']
                if location:
                    nearby_mobs = self._find_nearby_mobs(location)
                    if nearby_mobs:
                        mob_assignment["nearby_mobs"] = nearby_mobs
            
            # Cache the assignment with enhanced metadata
            video_id = analysis_results.get("video_id", "unknown_video")
            self._cache_assignment(
                video_id,
                mob_assignment,
                metadata
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
                "color_theme": self.mobs["active_milk_mob"]["color_theme"],
                "icon": self.mobs["active_milk_mob"]["icon"],
                "match_score": 0.5,
                "error": str(e)
            }
    
    def _analyze_with_llm(self, features, analysis_results):
        """
        Use LLM to analyze video content and suggest mob categorization
        
        Parameters:
        features (list): Extracted features from the video
        analysis_results (dict): Complete analysis results
        
        Returns:
        dict: LLM analysis results
        """
        # Prepare prompt with all video data
        prompt = f"""
        Analyze this milk drinking video and determine which thematic "Milk Mob" category it belongs in.
        
        Video analysis:
        - Objects detected: {', '.join(analysis_results.get('objects', []))}
        - Actions detected: {', '.join(analysis_results.get('actions', []))}
        - Description: {analysis_results.get('description', '')}
        - Semantic analysis: {analysis_results.get('semantic_analysis', '')}
        
        API responses:
        - Milk detection: {analysis_results.get('api_responses', {}).get('milk_question', '')}
        - Creativity assessment: {analysis_results.get('api_responses', {}).get('creativity_question', '')}
        
        Possible Milk Mob categories:
        1. active_milk_mob - Sports and fitness enthusiasts enjoying milk
        2. dance_milk_mob - Creative dancers incorporating milk
        3. chef_milk_mob - Culinary creations featuring milk
        4. comedy_milk_mob - Humorous and entertaining milk moments
        5. art_milk_mob - Artistic expressions with milk
        6. science_milk_mob - Scientific experiments and discoveries with milk
        7. extreme_milk_mob - Adventurous and daring milk challenges
        
        Determine the primary and secondary mob this video belongs to, with a confidence score (0-100) and explanation.
        Format your response as a JSON object with these keys:
        {{"primary_mob": "mob_id", "primary_confidence": 95, "secondary_mob": "mob_id", "secondary_confidence": 45, "explanation": "..."}}
        
        The primary_mob must be one of the mob_id values listed above. Be very specific with your answer.
        """
        
        # Call OpenAI API
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI that classifies milk drinking videos into thematic categories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Parse and return structured analysis
        try:
            content = response.choices[0].message.content
            # Look for JSON in response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                analysis = json.loads(json_str)
                return analysis
            else:
                # Fallback if JSON not found
                return {
                    "primary_mob": "active_milk_mob", 
                    "primary_confidence": 70,
                    "explanation": "Fallback classification due to parsing issues."
                }
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {
                "primary_mob": "active_milk_mob", 
                "primary_confidence": 70,
                "explanation": "Fallback classification due to parsing issues."
            }
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
                "total_videos": sum(count for _, count in mob_counts) if mob_counts else 0,
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
    def _cache_assignment(self, video_id, mob_assignment, metadata):
        """
        Cache the mob assignment in the database with enhanced metadata
        
        Parameters:
        video_id (str): Video ID
        mob_assignment (dict): Mob assignment information
        metadata (dict): Additional video metadata
        """
        try:
            conn = None
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mobs'")
            if not cursor.fetchone():
                logger.error("Mobs table does not exist, cannot cache assignment")
                return

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
            if not cursor.fetchone():
                logger.error("Videos table does not exist, cannot cache assignment")
                return
            
            # Extract locations and paths
            location_str = None
            if metadata and 'post_data' in metadata and 'location' in metadata['post_data']:
                location = metadata['post_data']['location']
                if location and isinstance(location, dict) and 'place_name' in location:
                    location_str = location['place_name']
            
            # Get video paths
            thumbnail_path = metadata.get('thumbnail_path', None) if metadata else None
            video_path = metadata.get('video_path', None) if metadata else None
            
            # Generate a title from the video_id if not provided
            title = f"Video {video_id[:8]}"
            if metadata and 'post_data' in metadata and 'caption' in metadata['post_data']:
                caption = metadata['post_data']['caption']
                if caption:
                    # Use first part of caption as title (max 50 chars)
                    title = caption[:50] + ('...' if len(caption) > 50 else '')
            
            # Description - combine caption and any API-generated description
            description = ""
            if metadata and 'post_data' in metadata and 'caption' in metadata['post_data']:
                description = metadata['post_data']['caption']
            
            cursor.execute("PRAGMA table_info(videos)")
            columns = [c[1] for c in cursor.fetchall()]

            if {'description', 'thumbnail_path', 'video_path'} <= set(columns):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO videos
                    (video_id, mob_id, title, description, thumbnail_path, video_path, location, match_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        video_id,
                        mob_assignment["mob_id"],
                        title,
                        description,
                        thumbnail_path,
                        video_path,
                        location_str,
                        mob_assignment["match_score"]
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO videos
                    (video_id, mob_id, title, location, match_score)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        video_id,
                        mob_assignment["mob_id"],
                        title,
                        location_str,
                        mob_assignment["match_score"]
                    )
                )
            
            cursor.execute("PRAGMA table_info(mobs)")
            mob_columns = [c[1] for c in cursor.fetchall()]
            if {'video_count', 'last_updated'} <= set(mob_columns):
                cursor.execute(
                    """
                    UPDATE mobs SET video_count = video_count + 1,
                    last_updated = CURRENT_TIMESTAMP
                    WHERE mob_id = ?
                    """,
                    (mob_assignment["mob_id"],)
                )
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error caching assignment: {str(e)}")
        finally:
            if conn:
                conn.close()
            logger.info(f"Video {video_id} assigned to {mob_assignment['mob_id']}")
    
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
                SELECT m.mob_id, m.name, m.description, m.color_theme, m.icon, m.video_count, m.cluster_id
                FROM mobs m
                ORDER BY m.video_count DESC
                """
            )
            
            rows = cursor.fetchall()
            
            mob_info = []
            
            for row in rows:
                mob_id, name, description, color_theme, icon, video_count, cluster_id = row
                
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
                
                # Get sample videos - enhanced query to include paths
                cursor.execute(
                    """
                    SELECT video_id, title, description, thumbnail_path, video_path, location, match_score
                    FROM videos
                    WHERE mob_id = ?
                    ORDER BY match_score DESC
                    LIMIT 3
                    """,
                    (mob_id,)
                )
                
                sample_videos = []
                for video_row in cursor.fetchall():
                    video_id, title, description, thumbnail_path, video_path, location, match_score = video_row
                    sample_videos.append({
                        "video_id": video_id,
                        "title": title,
                        "description": description,
                        "thumbnail_path": thumbnail_path,
                        "video_path": video_path,
                        "location": location,
                        "match_score": match_score
                    })
                
                mob_info.append({
                    "mob_id": mob_id,
                    "name": name,
                    "description": description,
                    "color_theme": color_theme,
                    "icon": icon,
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
                        "color_theme": data["color_theme"],
                        "icon": data["icon"],
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
                    "color_theme": data["color_theme"],
                    "icon": data["icon"],
                    "sample_keywords": data["keywords"][:5],
                    "video_count": 0,
                    "sample_videos": []
                })
            
            return mob_info
    
    def get_mob_videos(self, mob_id, limit=10):
        """
        Get videos for a specific mob
        
        Parameters:
        mob_id (str): Mob ID
        limit (int): Maximum number of videos to return
        
        Returns:
        list: Videos in the mob
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT video_id, title, description, thumbnail_path, video_path, location, match_score
                FROM videos
                WHERE mob_id = ?
                ORDER BY match_score DESC
                LIMIT ?
                """,
                (mob_id, limit)
            )
            
            videos = []
            for row in cursor.fetchall():
                video_id, title, description, thumbnail_path, video_path, location, match_score = row
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description,
                    "thumbnail_path": thumbnail_path,
                    "video_path": video_path,
                    "location": location,
                    "match_score": match_score
                })
            
            conn.close()
            return videos
            
        except Exception as e:
            logger.error(f"Error getting mob videos: {str(e)}")
            return []
    
    # The following methods are kept from the original implementation
    def _extract_features(self, analysis_results):
        """Extract relevant features from analysis results"""
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
        
        # Remove duplicates while preserving order
        unique_features = []
        seen = set()
        for feature in features:
            if feature not in seen:
                seen.add(feature)
                unique_features.append(feature)
        
        return unique_features
    
    def _extract_keywords_from_text(self, text):
        """Extract keywords from text, filtering out common words"""
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
        """Calculate match score between video features and mob category"""
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
        """Get breakdown of extracted features for explanation"""
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
        """Get mob data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get mob info with enhanced fields
            cursor.execute(
                """
                SELECT name, description, color_theme, icon, video_count
                FROM mobs
                WHERE mob_id = ?
                """,
                (mob_id,)
            )
            
            row = cursor.fetchone()
            
            if not row:
                return None
                
            name, description, color_theme, icon, video_count = row
            
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
                "color_theme": color_theme,
                "icon": icon,
                "video_count": video_count,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"Error getting mob data: {str(e)}")
            return None
    
    def _find_nearby_mobs(self, location, limit=3):
        """Find mobs near the given location"""
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
                SELECT v.mob_id, m.name, m.description, m.color_theme, m.icon, COUNT(v.video_id) as video_count
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
                mob_id, name, description, color_theme, icon, video_count = row
                
                nearby_mobs.append({
                    "mob_id": mob_id,
                    "name": name,
                    "description": description,
                    "color_theme": color_theme,
                    "icon": icon,
                    "location": place_name,
                    "video_count": video_count
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error finding nearby mobs: {str(e)}")
        
        return nearby_mobs
