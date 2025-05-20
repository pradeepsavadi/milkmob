import logging
import os
import json
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:  # pragma: no cover - openai may not be installed
    import openai
except Exception:  # pragma: no cover
    openai = None

class CampaignValidator:
    """
    Validates if a video meets the criteria for the Got Milk campaign using Twelve Labs API
    """
    def __init__(self, analyzer=None, openai_api_key=None):
        """
        Initialize the campaign validator with the VideoAnalyzer
        
        Parameters:
        analyzer: VideoAnalyzer instance for additional API calls
        """
        self.analyzer = analyzer
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self._openai_client = None
        if self.openai_api_key and openai:
            self._openai_client = openai.OpenAI(
                api_key=self.openai_api_key,
                http_client=httpx.Client(proxy=None, trust_env=False),
            )
        
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

    def _analyze_campaign_prompt(self, analysis: dict, metadata: dict | None):
        """Use OpenAI with a detailed campaign prompt to analyze the video."""
        if not self._openai_client:
            return None

        meta_parts = []
        if metadata:
            title = metadata.get("title") or metadata.get("caption") or ""
            user = metadata.get("user_id") or ""
            hashtags = " ".join(metadata.get("hashtags", [])) if metadata.get("hashtags") else ""
            duration = metadata.get("duration") or analysis.get("video_data", {}).get("duration", "")
            meta_parts.append(f"title={title}")
            if user:
                meta_parts.append(f"user={user}")
            if hashtags:
                meta_parts.append(f"hashtags={hashtags}")
            if duration:
                meta_parts.append(f"duration={duration}")
        video_meta = ", ".join(meta_parts)

        summary = analysis.get("summary", "")
        actions = ", ".join(analysis.get("actions", []))
        objects = ", ".join(analysis.get("objects", []))
        location = ""
        if metadata and isinstance(metadata.get("location"), dict):
            loc = metadata.get("location")
            location = f"{loc.get('place_name','')}, {loc.get('city','')}"

        prompt = (
            'You are an AI assistant for a social media platform\'s viral marketing campaign called "Got Milk Mob."\n'
            'Your task is to analyze video content and categorize it into appropriate "Milk Mobs" based on the following information extracted by Twelve Labs:\n\n'
            f'VIDEO METADATA:\n{video_meta}\n\n'
            f'VIDEO CONTENT SUMMARY:\n{summary}\n\n'
            f'KEY ACTIONS DETECTED:\n{actions}\n\n'
            f'OBJECTS IDENTIFIED:\n{objects}\n\n'
            f'SETTING/LOCATION:\n{location}\n\n'
            'INSTRUCTIONS:\n'
            '1. Verify this video is genuinely part of the "Got Milk" campaign by confirming:\n'
            '   - Presence of milk consumption or milk container\n'
            '   - Person performing a creative/unique activity while drinking milk\n'
            '   - Overall alignment with campaign theme\n\n'
            '2. If validated, categorize this video into one of the following "Milk Mobs" or suggest a new one:\n'
            '   - Sports Milk Mob (athletic activities)\n'
            '   - Dance Milk Mob (dancing/movement-based activities)\n'
            '   - Stunt Milk Mob (impressive tricks/stunts)\n'
            '   - Comedy Milk Mob (funny/humorous content)\n'
            '   - Challenge Milk Mob (completing specific challenges)\n'
            '   - [Other mob categories as appropriate]\n\n'
            '3. Provide a brief rationale (2-3 sentences) for your categorization.\n'
            '4. Generate 3-5 relevant hashtags that could be suggested to the user beyond #gotmilk and #milkmob.\n'
            '5. Identify 2-3 distinctive elements that could connect this video with others in the same "Milk Mob."\n\n'
            'Respond in JSON with keys campaign_validation, recommended_mob, rationale, hashtags, connection_points.'
        )

        try:
            resp = self._openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:  # pragma: no cover - network not available
            logger.warning("OpenAI campaign prompt failed: %s", e)
            return None

    def _analyze_with_llm(self, milk_text: str, creativity_text: str):
        """Use OpenAI to interpret the analysis text and return structured flags."""
        if not self._openai_client:
            return None
        prompt = (
            "Given the following analysis from the Twelve Labs API about a video, "
            "decide if the video clearly shows milk, if someone is drinking it, "
            "and whether it depicts food preparation or cheese making. "
            "Also provide a creativity score between 0 and 1.\n"
            f"Milk analysis: {milk_text}\n"
            f"Creativity analysis: {creativity_text}\n"
            "Respond in JSON with keys has_milk, is_drinking, is_food_prep, "
            "is_cheese_making, creativity_score, message."
        )
        try:
            resp = self._openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as e:  # pragma: no cover - network not available
            logger.warning("OpenAI classification failed: %s", e)
            return None

    def _detect_presence_in_text(self, text, subject):
        """Better detection of subject presence in text with negation handling"""
        if not text:
            return False

        text_lower = text.lower()
        negative_phrases = [
            "does not show " + subject,
            "doesn't show " + subject,
            "no " + subject,
            "not showing " + subject,
            "doesn't contain " + subject,
            "does not contain " + subject,
            "isn't " + subject,
            "is not " + subject,
            "not being consumed",
            "not consumed",
        ]
        if any(phrase in text_lower for phrase in negative_phrases):
            return False

        positive_phrases = [
            "shows " + subject,
            "contains " + subject,
            "has " + subject,
            "using " + subject,
            "with " + subject,
            subject + " is present",
            subject + " is shown",
            "dairy",
            "cheese",
        ]

        return any(phrase in text_lower for phrase in positive_phrases)

    def _detect_drinking_in_text(self, text):
        """Detect drinking activity in text with better accuracy"""
        if not text:
            return False

        text_lower = text.lower()
        negative_phrases = [
            "not drinking",
            "doesn't show drinking",
            "does not show drinking",
            "no drinking",
            "no one drinking",
            "no one is drinking",
            "not consumed",
            "not being consumed",
            "does not depict",
            "doesn't depict",
        ]
        if any(phrase in text_lower for phrase in negative_phrases):
            return False

        drinking_phrases = [
            "drinking",
            "sipping",
            "gulping",
            "consuming milk",
            "consuming the milk",
            "drinks milk",
            "drinking milk",
            "milk consumption",
        ]
        return any(phrase in text_lower for phrase in drinking_phrases)

    def _detect_food_preparation(self, text):
        """Detect food preparation activities in text"""
        if not text:
            return False

        text_lower = text.lower()
        food_prep_phrases = [
            "making",
            "cooking",
            "preparing",
            "recipe",
            "cheese",
            "cheese-making",
            "cheese making",
            "separation",
            "separating",
            "curds",
            "whey",
            "culinary",
            "food preparation",
            "kitchen",
        ]
        return any(phrase in text_lower for phrase in food_prep_phrases)
    
    def validate_video(self, analysis_results, tag_results=None, metadata=None):
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

            if self.analyzer and video_id:
                milk_question_prompt = "Does this video show milk or someone drinking milk? Explain how certain you are."
                milk_text = self.analyzer.client.generate.text(
                    video_id=video_id,
                    prompt=milk_question_prompt
                )

                creativity_question_prompt = "Is this video showing a creative or unique way of drinking milk? Rate creativity on a scale of 1-10."
                creativity_text = self.analyzer.client.generate.text(
                    video_id=video_id,
                    prompt=creativity_question_prompt
                )

                milk_response = milk_text.data if hasattr(milk_text, 'data') else ""
                creativity_response = creativity_text.data if hasattr(creativity_text, 'data') else ""

                llm_result = self._analyze_with_llm(milk_response, creativity_response)
                campaign_result = self._analyze_campaign_prompt(analysis_results, metadata)
                if llm_result:
                    has_milk = llm_result.get("has_milk", False)
                    is_drinking = llm_result.get("is_drinking", False)
                    is_food_prep = llm_result.get("is_food_prep", False)
                    is_cheese_making = llm_result.get("is_cheese_making", False)
                    creativity_confidence = llm_result.get("creativity_score", 0.0)
                else:
                    has_milk = self._detect_presence_in_text(milk_response, "milk")
                    is_drinking = self._detect_drinking_in_text(milk_response)
                    is_food_prep = self._detect_food_preparation(milk_response) or self._detect_food_preparation(creativity_response)
                    is_cheese_making = "cheese" in milk_response.lower() or "cheese-making" in milk_response.lower() or "cheese making" in milk_response.lower()
                    creativity_confidence = self._extract_creativity_score(creativity_response) / 10.0

                milk_confidence = self._extract_confidence_from_text(milk_response, "milk") if has_milk else 0.3

                tag_boost = 0.0
                if tag_results and tag_results.get("is_campaign_tagged", False):
                    tag_boost = min(0.2, tag_results.get("confidence_score", 0.0))
                    milk_confidence = min(1.0, milk_confidence + tag_boost)

                is_valid = has_milk and is_drinking and not is_cheese_making

                validation_result = {
                    "is_valid": is_valid,
                    "has_milk": has_milk,
                    "is_drinking": is_drinking,
                    "is_cheese_making": is_cheese_making,
                    "is_food_prep": is_food_prep,
                    "is_creative": creativity_confidence >= 0.5,
                    "milk_confidence": milk_confidence,
                    "drinking_confidence": 0.7 if is_drinking else 0.3,
                    "creativity_confidence": creativity_confidence,
                    "audio_confidence": analysis_results.get("audio_confidence", 0.0),
                    "overall_confidence": (milk_confidence + (0.7 if is_drinking else 0.3)) / 2.0,
                    "message": llm_result.get("message") if llm_result else None,
                    "mob_suggestion": None,
                    "api_responses": {
                        "milk_question": milk_response,
                        "creativity_question": creativity_response,
                    },
                }

                if campaign_result:
                    validation_result["is_valid"] = str(campaign_result.get("campaign_validation", "")).lower().startswith("y")
                    validation_result["mob_suggestion"] = campaign_result.get("recommended_mob")
                    validation_result["message"] = campaign_result.get("rationale", validation_result.get("message"))
                    validation_result["suggested_hashtags"] = campaign_result.get("hashtags", [])
                    validation_result["connection_points"] = campaign_result.get("connection_points", [])

                if is_cheese_making or is_food_prep:
                    validation_result["message"] = (
                        "Your video shows cheese-making or food preparation, which is a creative use of milk, but it doesn't show milk drinking as required for the campaign."
                    )
                    validation_result["mob_suggestion"] = "chef_milk_mob"
                else:
                    if not validation_result["message"]:
                        validation_result["message"] = self._generate_validation_message(
                            is_valid,
                            has_milk,
                            is_drinking,
                            creativity_confidence >= 0.5,
                            False,
                            tag_results,
                        )
                    if is_valid:
                        validation_result["mob_suggestion"] = "active_milk_mob"

                logger.info(f"Validation result: {validation_result['is_valid']}")
                return validation_result

            else:
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
            return f"Great job! Your video shows someone drinking milk!{tag_message} You're now ready to join a Milk Mob."
        elif not has_milk:
            return f"We couldn't detect milk in your video. Make sure milk is clearly visible.{tag_message}"
        elif not is_drinking:
            return f"We couldn't detect drinking activity. Make sure someone is drinking milk in the video.{tag_message}"
        else:
            return f"Your video doesn't meet all the campaign criteria. Please try again with more focus on milk drinking.{tag_message}"