import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignValidator:
    """
    Validates if a video meets the criteria for the Got Milk campaign using Twelve Labs API
    """
    def __init__(self, analyzer=None):
        """
        Initialize the campaign validator with the VideoAnalyzer
        
        Parameters:
        analyzer: VideoAnalyzer instance for additional API calls
        """
        self.analyzer = analyzer
        
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
    
    def validate_video(self, analysis_results, tag_results=None):
        """
        Validate if video meets campaign criteria using Twelve Labs API capabilities
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        tag_results (dict): Results from tag detection
        
        Returns:
        dict: Validation results
        """
        logger.info("Validating video against campaign criteria")
        
        try:
            video_id = analysis_results.get("video_id", None)
            
            # Instead of using generate.question which doesn't exist,
            # use generate.text with specific questions
            if self.analyzer and video_id:
                # Use the Twelve Labs generate.text API to directly ask about milk content
                milk_question_prompt = "Does this video show milk or someone drinking milk? Explain how certain you are."
                milk_text = self.analyzer.client.generate.text(
                    video_id=video_id,
                    prompt=milk_question_prompt
                )
                
                # Use the API to assess creativity
                creativity_question_prompt = "Is this video showing a creative or unique way of drinking milk? Rate creativity on a scale of 1-10."
                creativity_text = self.analyzer.client.generate.text(
                    video_id=video_id,
                    prompt=creativity_question_prompt
                )
                
                # Analyze the responses
                milk_response = milk_text.data if hasattr(milk_text, 'data') else ""
                creativity_response = creativity_text.data if hasattr(creativity_text, 'data') else ""
                
                # Extract confidence levels from API responses
                milk_confidence = self._extract_confidence_from_text(milk_response, "milk")
                creativity_confidence = self._extract_creativity_score(creativity_response) / 10.0
                
                # Get direct visual and audio confidence scores
                visual_confidence = analysis_results.get("visual_confidence", {})
                milk_visual_confidence = visual_confidence.get("has_milk", 0.0)
                drinking_confidence = visual_confidence.get("is_drinking", 0.0)
                audio_confidence = analysis_results.get("audio_confidence", 0.0)
                
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
                
                # Use the highest confidence values from all methods
                final_milk_confidence = max(milk_confidence, milk_visual_confidence)
                
                # Final validation decision
                has_milk = (final_milk_confidence >= 0.6) or has_milk_by_terms
                is_drinking = (drinking_confidence >= 0.6) or is_drinking_by_terms
                is_creative = creativity_confidence >= 0.5
                has_audio_mention = audio_confidence >= 0.6
                
                # Tag boost
                tag_boost = 0.0
                if tag_results and tag_results.get("is_campaign_tagged", False):
                    tag_boost = min(0.2, tag_results.get("confidence_score", 0.0))
                    final_milk_confidence = min(1.0, final_milk_confidence + tag_boost)
                    
                # Overall validation result - must have milk and drinking activity
                is_valid = has_milk and is_drinking
                
                # Overall confidence score
                overall_confidence = (final_milk_confidence + drinking_confidence) / 2.0
                
                # Generate validation results
                validation_result = {
                    "is_valid": is_valid,
                    "has_milk": has_milk,
                    "is_drinking": is_drinking,
                    "is_creative": is_creative,
                    "has_audio_mention": has_audio_mention,
                    "milk_confidence": final_milk_confidence,
                    "drinking_confidence": drinking_confidence,
                    "creativity_confidence": creativity_confidence,
                    "audio_confidence": audio_confidence,
                    "tag_boost": tag_boost,
                    "overall_confidence": overall_confidence,
                    "message": self._generate_validation_message(
                        is_valid, has_milk, is_drinking, is_creative, has_audio_mention, tag_results
                    ),
                    "api_responses": {
                        "milk_question": milk_response,
                        "creativity_question": creativity_response
                    }
                }
                
                logger.info(f"Validation result: {validation_result['is_valid']}")
                return validation_result
            
            else:
                # Fallback to basic analysis if generate API isn't available
                return self._basic_validation(analysis_results, tag_results)
                
        except Exception as e:
            logger.error(f"Error validating video: {str(e)}")
            return {
                "is_valid": False,
                "error": str(e),
                "message": "Failed to validate video due to an error."
            }
    
    def _extract_confidence_from_text(self, text, topic):
        """
        Extract confidence level from text generated by Twelve Labs API
        
        Parameters:
        text (str): Text response from the API
        topic (str): Topic to extract confidence for
        
        Returns:
        float: Confidence level between 0 and 1
        """
        # Look for confidence indicators in the text
        high_confidence_terms = ["definitely", "certainly", "clearly", "100%", "very certain", "absolutely"]
        medium_confidence_terms = ["likely", "probably", "seems", "appears", "I think", "mostly"]
        low_confidence_terms = ["possibly", "might", "maybe", "uncertain", "not clear", "doubt"]
        negative_terms = ["no", "not", "doesn't", "isn't", "couldn't", "can't find"]
        
        # Default medium confidence
        confidence = 0.6
        
        # Check for negative statements
        if any(term in text.lower() for term in negative_terms):
            confidence -= 0.3
        
        # Adjust based on confidence terms
        if any(term in text.lower() for term in high_confidence_terms):
            confidence += 0.3
        elif any(term in text.lower() for term in medium_confidence_terms):
            confidence += 0.1
        elif any(term in text.lower() for term in low_confidence_terms):
            confidence -= 0.1
            
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    def _extract_creativity_score(self, text):
        """
        Extract creativity score from text generated by Twelve Labs API
        
        Parameters:
        text (str): Text response from the API
        
        Returns:
        float: Creativity score between 1 and 10
        """
        # Try to find a numeric score in the text
        import re
        
        # Look for patterns like "8/10" or "score of 7" or "rating: 6"
        score_patterns = [
            r"(\d+)(?:\s*\/\s*10)",  # 8/10
            r"score of (\d+)",        # score of 7
            r"rating:?\s*(\d+)",      # rating: 6
            r"(\d+)(?:\s*out of\s*10)"  # 8 out of 10
        ]
        
        for pattern in score_patterns:
            matches = re.search(pattern, text.lower())
            if matches:
                try:
                    score = int(matches.group(1))
                    # Ensure score is between 1 and 10
                    return max(1, min(10, score))
                except:
                    pass
        
        # If no numeric score found, estimate based on language
        if "highly creative" in text.lower() or "very creative" in text.lower():
            return 8
        elif "creative" in text.lower():
            return 6
        elif "somewhat creative" in text.lower():
            return 5
        else:
            return 3  # Default score
    
    def _basic_validation(self, analysis_results, tag_results):
        """
        Basic validation using only analysis results
        
        Parameters:
        analysis_results (dict): Results from the video analysis
        tag_results (dict): Results from tag detection
        
        Returns:
        dict: Validation results
        """
        # Extract visual confidence scores from analysis
        visual_confidence = analysis_results.get("visual_confidence", {})
        
        milk_confidence = visual_confidence.get("has_milk", 0.0)
        drinking_confidence = visual_confidence.get("is_drinking", 0.0)
        creativity_confidence = visual_confidence.get("is_creative", 0.0)
        
        # Get audio confidence
        audio_confidence = analysis_results.get("audio_confidence", 0.0)
        
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
        
        # Final validation checks
        has_milk = (milk_confidence >= 0.6) or has_milk_by_terms
        is_drinking = (drinking_confidence >= 0.6) or is_drinking_by_terms
        is_creative = (creativity_confidence >= 0.5)
        has_audio_mention = audio_confidence >= 0.6
        
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
            "has_audio_mention": has_audio_mention,
            "milk_confidence": milk_confidence,
            "drinking_confidence": drinking_confidence,
            "creativity_confidence": creativity_confidence,
            "audio_confidence": audio_confidence,
            "overall_confidence": overall_confidence,
            "message": self._generate_validation_message(
                is_valid, has_milk, is_drinking, is_creative, has_audio_mention, tag_results
            ),
        }
        
        logger.info(f"Basic validation result: {validation_result['is_valid']}")
        return validation_result
    
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
    
    def _generate_validation_message(self, is_valid, has_milk, is_drinking, is_creative, has_audio_mention, tag_results=None):
        """
        Generate user-friendly validation message
        
        Parameters:
        is_valid (bool): Overall validation result
        has_milk (bool): Has milk-related objects
        is_drinking (bool): Has drinking activity
        is_creative (bool): Has creative elements
        has_audio_mention (bool): Has milk-related audio
        tag_results (dict): Results from tag detection
        
        Returns:
        str: User-friendly message
        """
        # Message about hashtags
        tag_message = ""
        if tag_results:
            if tag_results.get("is_campaign_tagged", False):
                tag_message = f" Your hashtags {', '.join(tag_results['campaign_tags_found'])} were recognized!"
            else:
                tag_message = " Don't forget to include campaign hashtags like #gotmilk or #milkmob!"
        
        if is_valid:
            if is_creative:
                return f"Great job! Your video shows someone creatively drinking milk!{tag_message} You're now ready to join a Milk Mob."
            else:
                return f"Good job! Your video shows milk drinking.{tag_message} To make it even better, try adding more creative elements."
        elif not has_milk:
            return f"We couldn't detect milk in your video. Make sure milk is clearly visible.{tag_message}"
        elif not is_drinking:
            return f"We couldn't detect drinking activity. Make sure someone is drinking milk in the video.{tag_message}"
        else:
            return f"Your video doesn't meet all the campaign criteria. Please try again with more focus on milk drinking.{tag_message}"