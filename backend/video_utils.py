import os
import uuid
import logging
import time
import numpy as np
from datetime import datetime
from PIL import Image
import io

# Initialize logging
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

def extract_thumbnail(analysis_results, video_path, thumbnails_dir="thumbnails"):
    """
    Extract thumbnail from video analysis or storyboard
    
    Parameters:
    analysis_results (dict): Results from video analysis
    video_path (str): Path to the video file
    thumbnails_dir (str): Directory to save thumbnails
    
    Returns:
    str: Path to the thumbnail file
    """
    os.makedirs(thumbnails_dir, exist_ok=True)
    
    # Generate thumbnail filename based on video filename
    video_basename = os.path.basename(video_path)
    thumbnail_filename = f"{os.path.splitext(video_basename)[0]}_thumb.jpg"
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
    
    # Try to get thumbnail from storyboard if available
    storyboard = None
    if analysis_results and "analysis_results" in analysis_results:
        storyboard = analysis_results["analysis_results"].get("storyboard")
        
    if storyboard and len(storyboard) > 0:
        try:
            # Use first frame from storyboard - this would typically involve 
            # downloading the image from a URL provided by Twelve Labs
            # For demo purposes, we'll just use a placeholder
            create_placeholder_thumbnail(thumbnail_path)
            logger.info(f"Thumbnail created from storyboard at {thumbnail_path}")
            return os.path.abspath(thumbnail_path)
        except Exception as e:
            logger.warning(f"Failed to create thumbnail from storyboard: {str(e)}")
    
    # Fallback: Create a placeholder thumbnail
    try:
        create_placeholder_thumbnail(thumbnail_path)
        logger.info(f"Placeholder thumbnail created at {thumbnail_path}")
        return os.path.abspath(thumbnail_path)
    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        return None

def create_placeholder_thumbnail(thumbnail_path):
    """Create a placeholder thumbnail image"""
    try:
        # Create a simple colored rectangle as placeholder
        img = Image.new('RGB', (640, 360), color=(73, 109, 137))
        try:
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "MilkMob", fill=(255, 255, 255))
        except Exception:
            pass
        img.save(thumbnail_path)
    except Exception as e:
        logger.error(f"Error creating placeholder thumbnail: {str(e)}")
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
        
        # Extract thumbnail
        thumbnail_path = extract_thumbnail(analysis_results, video_path)
        
        # Extract caption and storyboard if available
        caption = None
        storyboard = None
        if analysis_results and "analysis_results" in analysis_results:
            caption = analysis_results["analysis_results"].get("caption")
            storyboard = analysis_results["analysis_results"].get("storyboard")
        
        # Ensure validator has access to analyzer for API calls
        validator.analyzer = analyzer
        
        # Step 3: Validate against campaign criteria
        validation_result = validator.validate_video(
            analysis_results["analysis_results"],
            tag_results,
<<<<<<< HEAD
            post_data
=======
            post_data,
>>>>>>> main
        )
        
        # Step 4: Always classify, even if not valid
        mob_assignment = classifier.classify_video(
            analysis_results["analysis_results"],
            {
                "post_data": post_data,
                "thumbnail_path": thumbnail_path,
                "video_path": video_path,
                "validation": validation_result,
            }
        )

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
            "processing_time": processing_time,
            "caption": caption,
            "storyboard": storyboard,
            "thumbnail_path": thumbnail_path
        }
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return {
            "status": "error",
            "video_path": video_path,
            "error": str(e)
        }