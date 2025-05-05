import os
import uuid
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_uploaded_video(uploaded_file, videos_dir="videos"):
    """
    Save an uploaded video file to the videos directory
    
    Parameters:
    uploaded_file: StreamlitUploadedFile or similar object
    videos_dir (str): Directory to save videos
    
    Returns:
    str: Path to the saved video file
    """
    # Create videos directory if it doesn't exist
    os.makedirs(videos_dir, exist_ok=True)
    
    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{uploaded_file.name}"
    
    # Save file path
    file_path = os.path.join(videos_dir, filename)
    
    # Save the file
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        logger.info(f"Video saved to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving video: {str(e)}")
        raise

def process_video_post(video_path, post_data, analyzer, validator, classifier, tag_detector):
    """
    Process a video post through the entire pipeline
    
    Parameters:
    video_path (str): Path to the video file
    post_data (dict): Post data including caption, hashtags, location
    analyzer (VideoAnalyzer): Instance of VideoAnalyzer
    validator (CampaignValidator): Instance of CampaignValidator
    classifier (MilkMobClassifier): Instance of MilkMobClassifier
    tag_detector (CampaignTagDetector): Instance of CampaignTagDetector
    
    Returns:
    dict: Processing results
    """
    start_time = time.time()
    logger.info(f"Starting video processing pipeline for {video_path}")
    
    try:
        # Step 1: Detect campaign tags
        tag_results = tag_detector.detect_tags(post_data)
        
        # Extract location data if available
        location = None
        if "location" in post_data and post_data["location"]:
            location = post_data["location"]
        
        # Step 2: Analyze video with Twelve Labs
        analysis_results = analyzer.upload_and_analyze_video(video_path)
        
        # Ensure validator has access to analyzer for API calls
        validator.analyzer = analyzer
        
        # Step 3: Validate against campaign criteria
        validation_result = validator.validate_video(
            analysis_results["analysis_results"], 
            tag_results
        )
        
        # Step 4: If valid, classify into a Milk Mob
        mob_assignment = None
        similar_videos = []
        
        if validation_result["is_valid"]:
            mob_assignment = classifier.classify_video(
                analysis_results["analysis_results"], 
                location
            )
            # Find similar videos in the same mob
            similar_videos = analyzer.find_similar_videos(analysis_results["video_id"])
        
        # Complete processing time
        processing_time = time.time() - start_time
        
        return {
            "status": "success",
            "video_path": video_path,
            "video_id": analysis_results["video_id"],
            "post_data": post_data,
            "tag_results": tag_results,
            "validation": validation_result,
            "mob_assignment": mob_assignment,
            "similar_videos": similar_videos,
            "location": location,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return {
            "status": "error",
            "video_path": video_path,
            "error": str(e)
        }