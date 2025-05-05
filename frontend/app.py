import streamlit as st
import os
import sys
import time

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import backend components
from backend.analyzer import VideoAnalyzer
from backend.validator import CampaignValidator
from backend.classifier import MilkMobClassifier
from backend.utils import save_uploaded_video, process_video

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="MilkMob Analyzer",
    page_icon="🥛",
    layout="wide"
)

# App title and description
st.title("🥛 Got Milk Campaign Validator")
st.markdown("""
This application helps validate and categorize videos for the "Got Milk" viral campaign.
Upload your video showing creative milk drinking, and we'll analyze it using AI!
""")

# Initialize components
@st.cache_resource
def load_components():
    api_key = os.getenv("TWELVE_LABS_API_KEY")
    index_id = os.getenv("TWELVE_LABS_INDEX_ID", "milk_campaign_index")
    
    if not api_key:
        st.error("Twelve Labs API key not found. Please set it in the .env file.")
        st.stop()
    
    analyzer = VideoAnalyzer(api_key=api_key, index_id=index_id)
    validator = CampaignValidator()
    classifier = MilkMobClassifier()
    
    return analyzer, validator, classifier

analyzer, validator, classifier = load_components()

# Create tabs for different app sections
tab1, tab2 = st.tabs(["Upload & Validate", "Explore Milk Mobs"])

# Upload & Validate tab
with tab1:
    st.subheader("Upload Your Video")
    st.write("Share your creative milk drinking video to join a Milk Mob!")
    
    # Video upload
    video_file = st.file_uploader("Choose a video file", type=["mp4", "mov", "avi"])
    hashtag = st.text_input("Enter your hashtag (e.g. #gotmilk, #milkmob)", "#gotmilk")
    
    if video_file and st.button("Process Video"):
        # Save uploaded video to videos folder
        try:
            video_path = save_uploaded_video(video_file)
            st.success(f"Video uploaded successfully!")
            
            # Process the video
            with st.spinner("Analyzing video content... This may take a minute..."):
                results = process_video(video_path, analyzer, validator, classifier)
            
            if results["status"] == "success":
                # Show validation result
                if results["validation"]["is_valid"]:
                    st.success("✅ Video validated successfully!")
                    
                    # Show mob assignment
                    mob = results["mob_assignment"]
                    st.subheader(f"You've joined the {mob['mob_name']}! 🎉")
                    st.write(mob["mob_description"])
                    
                    # Display analysis details in an expander
                    with st.expander("View Analysis Details"):
                        st.json(results["validation"])
                    
                    # Show similar videos if available
                    if results["similar_videos"]:
                        st.subheader("Similar videos in your Milk Mob:")
                        for video in results["similar_videos"]:
                            st.write(f"- {video['title']} (Similarity: {video['similarity_score']:.2f})")
                else:
                    st.error("❌ Video validation failed")
                    st.write(results["validation"]["message"])
                    st.write("Please ensure your video shows someone drinking milk creatively!")
                    
                    # Display analysis details in an expander
                    with st.expander("View Validation Details"):
                        st.json(results["validation"])
            else:
                st.error(f"Error processing video: {results['error']}")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Explore Milk Mobs tab
with tab2:
    st.subheader("Explore Milk Mobs")
    st.write("Learn about the different Milk Mobs you can join with your creative milk videos!")
    
    # Get all mob information
    all_mobs = classifier.get_all_mobs()
    
    # Display mobs in a grid
    cols = st.columns(3)
    
    for i, mob in enumerate(all_mobs):
        with cols[i % 3]:
            st.markdown(f"### {mob['name']}")
            st.write(mob['description'])
            st.write("**Sample Keywords:**")
            for keyword in mob['sample_keywords']:
                st.write(f"- {keyword}")
            st.write("---")

# Footer
st.markdown("---")
st.write("Powered by Twelve Labs Video Understanding API")