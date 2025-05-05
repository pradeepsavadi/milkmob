import re
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignTagDetector:
    """
    Detects campaign-related hashtags in social media post content
    """
    def __init__(self, campaign_tags=None):
        """
        Initialize the campaign tag detector
        
        Parameters:
        campaign_tags (list): List of campaign-related hashtags to detect
        """
        self.campaign_tags = campaign_tags or [
            "#gotmilk", "#milkmob", "#gotmilk2025", "#milkchallenge",
            "#milkitup", "#drinkmoremilk", "#milkmovement"
        ]
        
        # Compile regex patterns for tag detection
        self.tag_pattern = re.compile(r'#\w+')
        
        # Keep track of popular tags for analytics
        self.tag_counter = Counter()
    
    def detect_tags(self, post_data):
        """
        Detect campaign hashtags in post data
        
        Parameters:
        post_data (dict): Post data containing caption, hashtags, location
        
        Returns:
        dict: Tag detection results
        """
        logger.info("Detecting campaign tags in post data")
        
        # Initialize result
        result = {
            "is_campaign_tagged": False,
            "campaign_tags_found": [],
            "all_tags_found": [],
            "confidence_score": 0.0
        }
        
        try:
            # Extract hashtags from various sources
            hashtags = []
            
            # From specific hashtags field if available
            if "hashtags" in post_data and isinstance(post_data["hashtags"], list):
                hashtags.extend(post_data["hashtags"])
            
            # From caption if available
            if "caption" in post_data and post_data["caption"]:
                caption_tags = self.tag_pattern.findall(post_data["caption"])
                hashtags.extend(caption_tags)
            
            # Normalize hashtags (lowercase and remove duplicates)
            normalized_hashtags = [tag.lower() for tag in hashtags]
            result["all_tags_found"] = list(set(normalized_hashtags))
            
            # Check for campaign tags
            campaign_tags_found = []
            for tag in normalized_hashtags:
                if any(campaign_tag.lower() in tag for campaign_tag in self.campaign_tags):
                    campaign_tags_found.append(tag)
            
            # Update result
            result["is_campaign_tagged"] = len(campaign_tags_found) > 0
            result["campaign_tags_found"] = campaign_tags_found
            
            # Calculate confidence based on number of matching tags
            result["confidence_score"] = min(1.0, len(campaign_tags_found) / 2.0)
            
            # Update tag counter for analytics
            self.tag_counter.update(campaign_tags_found)
            
            logger.info(f"Campaign tagged: {result['is_campaign_tagged']}")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting campaign tags: {str(e)}")
            return result
    
    def get_popular_tags(self, limit=10):
        """
        Get the most popular campaign tags
        
        Parameters:
        limit (int): Maximum number of tags to return
        
        Returns:
        list: Most popular tags with counts
        """
        return self.tag_counter.most_common(limit)
    
    def extract_metadata(self, post_data):
        """
        Extract all relevant metadata from the post
        
        Parameters:
        post_data (dict): Post data containing caption, hashtags, location
        
        Returns:
        dict: Extracted metadata
        """
        metadata = {}
        
        # Extract location if available
        if "location" in post_data and post_data["location"]:
            metadata["location"] = post_data["location"]
        
        # Extract caption if available
        if "caption" in post_data and post_data["caption"]:
            metadata["caption"] = post_data["caption"]
        
        # Extract relevant mentions
        if "caption" in post_data and post_data["caption"]:
            mentions = re.findall(r'@\w+', post_data["caption"])
            if mentions:
                metadata["mentions"] = mentions
        
        # Include any other custom fields
        for key in ["user_id", "post_time", "device", "app_version"]:
            if key in post_data:
                metadata[key] = post_data[key]
        
        return metadata