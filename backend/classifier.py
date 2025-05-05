import logging
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MilkMobClassifier:
    """
    Classifies valid videos into thematic "Milk Mobs"
    """
    def __init__(self):
        """Initialize the Milk Mob classifier with predefined mob categories"""
        # Define mob categories with keywords and descriptions
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
    
    def classify_video(self, analysis_results):
        """
        Assign video to appropriate milk mob based on content
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        
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
            
            mob_assignment = {
                "mob_id": best_mob[0],
                "mob_name": self.mobs[best_mob[0]]["name"],
                "mob_description": self.mobs[best_mob[0]]["description"],
                "match_score": best_mob[1],
                "secondary_mob": {
                    "mob_id": secondary_mob[0],
                    "mob_name": self.mobs[secondary_mob[0]]["name"],
                    "match_score": secondary_mob[1]
                } if secondary_mob else None,
                "feature_breakdown": self._get_feature_breakdown(features)
            }
            
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
        
        # Extract keywords from scenes
        if "scenes" in analysis_results:
            for scene in analysis_results["scenes"]:
                # Extract individual words, filtering out common words
                words = self._extract_keywords_from_text(scene)
                features.extend(words)
        
        # Extract keywords from conversations
        if "conversations" in analysis_results:
            for conversation in analysis_results["conversations"]:
                words = self._extract_keywords_from_text(conversation)
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
    
    def get_all_mobs(self):
        """
        Get information about all defined mobs
        
        Returns:
        list: Information about all mobs
        """
        mob_info = []
        
        for mob_id, data in self.mobs.items():
            mob_info.append({
                "mob_id": mob_id,
                "name": data["name"],
                "description": data["description"],
                "sample_keywords": data["keywords"][:5]  # Return just a sample of keywords
            })
        
        return mob_info