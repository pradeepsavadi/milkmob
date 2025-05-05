import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignValidator:
    """
    Validates if a video meets the criteria for the Got Milk campaign
    """
    def __init__(self, milk_threshold=0.6, drinking_threshold=0.6, creativity_threshold=0.5):
        """
        Initialize the campaign validator with thresholds
        
        Parameters:
        milk_threshold (float): Confidence threshold for milk presence
        drinking_threshold (float): Confidence threshold for drinking activity
        creativity_threshold (float): Confidence threshold for creative activity
        """
        self.milk_threshold = milk_threshold
        self.drinking_threshold = drinking_threshold
        self.creativity_threshold = creativity_threshold
        
        # Define key terms for validation
        self.milk_terms = [
            "milk", "bottle", "carton", "glass", "cup", "dairy"
        ]
        
        self.drinking_terms = [
            "drink", "sip", "gulp", "swallow", "consume"
        ]
        
        self.creativity_terms = [
            "creative", "unique", "interesting", "unusual", "artistic", 
            "dance", "jump", "flip", "trick", "stunt"
        ]
    
    def validate_video(self, analysis_results):
        """
        Validate if video meets campaign criteria
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        
        Returns:
        dict: Validation results
        """
        logger.info("Validating video against campaign criteria")
        
        try:
            # Check confidence scores from analysis
            confidence_scores = analysis_results.get("confidence_scores", {})
            
            milk_confidence = confidence_scores.get("has_milk", 0.0)
            drinking_confidence = confidence_scores.get("is_drinking", 0.0)
            creativity_confidence = confidence_scores.get("is_creative", 0.0)
            
            # Check for milk-related objects using terms
            has_milk_by_terms = self._contains_terms(
                analysis_results.get("objects", []),
                self.milk_terms
            )
            
            # Check for drinking activities using terms
            is_drinking_by_terms = self._contains_terms(
                analysis_results.get("actions", []),
                self.drinking_terms
            )
            
            # Check for creative elements using terms in scenes and actions
            is_creative_by_terms = (
                self._contains_terms(
                    analysis_results.get("actions", []),
                    self.creativity_terms
                ) or
                self._contains_terms_in_text(
                    analysis_results.get("scenes", []),
                    self.creativity_terms
                )
            )
            
            # Final validation checks
            has_milk = (milk_confidence >= self.milk_threshold) or has_milk_by_terms
            is_drinking = (drinking_confidence >= self.drinking_threshold) or is_drinking_by_terms
            is_creative = (creativity_confidence >= self.creativity_threshold) or is_creative_by_terms
            
            # Overall validation result
            is_valid = has_milk and is_drinking
            
            # Calculate overall confidence score
            overall_confidence = (milk_confidence + drinking_confidence) / 2.0
            
            # Generate detailed validation results
            validation_result = {
                "is_valid": is_valid,
                "has_milk": has_milk,
                "is_drinking": is_drinking,
                "is_creative": is_creative,
                "milk_confidence": milk_confidence,
                "drinking_confidence": drinking_confidence,
                "creativity_confidence": creativity_confidence,
                "overall_confidence": overall_confidence,
                "message": self._generate_validation_message(
                    is_valid, has_milk, is_drinking, is_creative
                ),
            }
            
            logger.info(f"Validation result: {validation_result['is_valid']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating video: {str(e)}")
            return {
                "is_valid": False,
                "error": str(e),
                "message": "Failed to validate video due to an error."
            }
    
    def _contains_terms(self, items, target_terms):
        """
        Check if any target terms are in the items list
        
        Parameters:
        items (list): List of strings to check
        target_terms (list): Terms to look for
        
        Returns:
        bool: True if any term is found
        """
        if not items:
            return False
            
        items_lower = [item.lower() for item in items]
        
        for term in target_terms:
            for item in items_lower:
                if term.lower() in item:
                    return True
        
        return False
    
    def _contains_terms_in_text(self, texts, target_terms):
        """
        Check if any target terms are in the text items
        
        Parameters:
        texts (list): List of text strings to check
        target_terms (list): Terms to look for
        
        Returns:
        bool: True if any term is found
        """
        if not texts:
            return False
            
        for text in texts:
            text_lower = text.lower()
            for term in target_terms:
                if term.lower() in text_lower:
                    return True
        
        return False
    
    def _generate_validation_message(self, is_valid, has_milk, is_drinking, is_creative):
        """
        Generate user-friendly validation message
        
        Parameters:
        is_valid (bool): Overall validation result
        has_milk (bool): Has milk-related objects
        is_drinking (bool): Has drinking activity
        is_creative (bool): Has creative elements
        
        Returns:
        str: User-friendly message
        """
        if is_valid:
            if is_creative:
                return "Great job! Your video shows someone creatively drinking milk! You're now ready to join a Milk Mob."
            else:
                return "Good job! Your video shows milk drinking. To make it even better, try adding more creative elements."
        elif not has_milk:
            return "We couldn't detect milk in your video. Make sure milk is clearly visible."
        elif not is_drinking:
            return "We couldn't detect drinking activity. Make sure someone is drinking milk in the video."
        else:
            return "Your video doesn't meet all the campaign criteria. Please try again with more focus on milk drinking."