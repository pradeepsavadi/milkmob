import streamlit as st
import os
import sys
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import backend components
from backend.analyzer import VideoAnalyzer
from backend.validator import CampaignValidator
from backend.classifier import MilkMobClassifier
from backend.tag_detector import CampaignTagDetector
from backend.utils import save_uploaded_video, process_video_post

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
st.title("🥛 Got Milk Campaign Validator & Analyzer")
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
    validator = CampaignValidator()  # We'll set the analyzer during processing
    classifier = MilkMobClassifier()
    tag_detector = CampaignTagDetector()
    
    return analyzer, validator, classifier, tag_detector

analyzer, validator, classifier, tag_detector = load_components()

# Create tabs for different app sections
tab1, tab2, tab3 = st.tabs(["Upload & Validate", "Explore Milk Mobs", "Dashboard"])

# Upload & Validate tab
with tab1:
    st.subheader("Upload Your Video")
    st.write("Share your creative milk drinking video to join a Milk Mob!")
    
    # Video upload
    video_file = st.file_uploader("Choose a video file", type=["mp4", "mov", "avi"])
    
    # Post metadata
    st.subheader("Post Details")
    caption = st.text_area("Caption", placeholder="Write your post caption here...")
    hashtags = st.text_input("Hashtags", placeholder="#gotmilk #milkmob")
    
    # Location information
    location_col1, location_col2 = st.columns(2)
    with location_col1:
        location_name = st.text_input("Location Name", placeholder="e.g. Central Park")
    with location_col2:
        city = st.text_input("City", placeholder="e.g. New York")
    
    # Process video button
    if video_file and st.button("Process Video"):
        # Save uploaded video to videos folder
        try:
            video_path = save_uploaded_video(video_file)
            st.success(f"Video uploaded successfully!")
            
            # Prepare post data
            post_data = {
                "caption": caption,
                "hashtags": hashtags.split() if hashtags else [],
                "location": {
                    "place_name": location_name,
                    "city": city
                } if location_name else None,
                "post_time": datetime.now().isoformat(),
                "user_id": "demo_user_123"  # In a real app, this would be the user's ID
            }
            
            # Process the video
            with st.spinner("Analyzing video content... This may take a minute..."):
                results = process_video_post(
                    video_path, 
                    post_data, 
                    analyzer, 
                    validator, 
                    classifier,
                    tag_detector
                )
            
            if results["status"] == "success":
                # Show validation result
                if results["validation"]["is_valid"]:
                    st.success("✅ Video validated successfully!")
                    
                    # Show mob assignment
                    mob = results["mob_assignment"]
                    st.subheader(f"You've joined the {mob['mob_name']}! 🎉")
                    st.write(mob["mob_description"])
                    
                    # Show hashtag detection results
                    if results["tag_results"]["is_campaign_tagged"]:
                        st.success(f"Campaign hashtags detected: {', '.join(results['tag_results']['campaign_tags_found'])}")
                    else:
                        st.warning("No campaign hashtags detected. Consider adding tags like #gotmilk or #milkmob to your post!")
                    
                    # Display location info if available
                    if "location" in results and results["location"]:
                        st.write(f"📍 Location: {results['location']['place_name']}, {results['location']['city']}")
                        
                        # Show nearby mobs if available
                        if "nearby_mobs" in mob and mob["nearby_mobs"]:
                            st.subheader("Nearby Milk Mobs:")
                            for nearby_mob in mob["nearby_mobs"]:
                                st.write(f"- {nearby_mob['name']} ({nearby_mob['video_count']} videos in {nearby_mob['location']})")
                    
                     # Display API responses
                    if "api_responses" in results["validation"]:
                        with st.expander("Twelve Labs API Analysis"):
                            st.subheader("Milk Detection")
                            st.write(results["validation"]["api_responses"]["milk_question"])
                            st.subheader("Creativity Assessment")
                            st.write(results["validation"]["api_responses"]["creativity_question"])                    
                    # Display analysis details in an expander
                    with st.expander("View Technical Details"):
                        st.json(results["validation"])
                    
                    # Show similar videos if available
                    if results["similar_videos"]:
                        st.subheader("Similar videos in your Milk Mob:")
                        for video in results["similar_videos"]:
                            st.write(f"- {video['title']} (Similarity: {video['similarity_score']:.2f})")
                        
                    # Generate shareable link
                    share_link = f"https://example.com/milkmob?mob={mob['mob_id']}&video={results['video_id']}"
                    st.text_input("Share your Milk Mob with friends!", value=share_link)
                    if st.button("Copy Link"):
                        st.success("Link copied to clipboard!")
                    
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
    col1, col2 = st.columns(2)
    
    for i, mob in enumerate(all_mobs):
        with col1 if i % 2 == 0 else col2:
            with st.expander(f"🥛 {mob['name']} ({mob['video_count']} videos)"):
                st.write(mob['description'])
                
                st.write("**Sample Keywords:**")
                for keyword in mob['sample_keywords']:
                    st.write(f"- {keyword}")
                
                # Show sample videos if available
                if mob['sample_videos']:
                    st.write("**Top Videos:**")
                    for video in mob['sample_videos']:
                        st.write(f"- {video['title']}")
                        if video.get('location'):
                            st.write(f"  📍 {video['location']}")
                
                # Add join button
                if st.button(f"Join {mob['name']}", key=f"join_{mob['mob_id']}"):
                    st.success(f"Upload your video to join {mob['name']}!")
                    # This is just for demo - would actually switch tabs in a real app
                    st.write("Go to the 'Upload & Validate' tab to upload your video.")

# Dashboard tab
with tab3:
    st.subheader("Milk Mob Dashboard")
    st.write("Analytics and insights about the Got Milk campaign")
    
    # Get mob statistics
    mob_stats = classifier.get_mob_stats()
    
    # Create metrics row
    metric1, metric2, metric3 = st.columns(3)
    with metric1:
        st.metric("Total Videos", mob_stats["total_videos"])
    with metric2:
        st.metric("Total Milk Mobs", mob_stats["total_mobs"])
    with metric3:
        st.metric("Campaign Hashtags", len(tag_detector.get_popular_tags()))
    
    # Create charts row
    chart1, chart2 = st.columns(2)
    
    with chart1:
        st.subheader("Mob Popularity")
        if mob_stats["mob_counts"]:
            mob_df = pd.DataFrame(mob_stats["mob_counts"], columns=["Mob", "Videos"])
            fig = px.bar(
                mob_df, 
                x="Mob", 
                y="Videos", 
                color="Videos",
                title="Videos per Milk Mob"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No mob data available yet. Upload some videos to see statistics!")
    
    with chart2:
        st.subheader("Geographic Distribution")
        if mob_stats["location_distribution"]:
            loc_df = pd.DataFrame(mob_stats["location_distribution"], columns=["Location", "Videos"])
            fig = px.pie(
                loc_df, 
                values="Videos", 
                names="Location",
                title="Videos by Location"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No location data available yet. Upload videos with location to see statistics!")
    
    # Top videos section
    st.subheader("Top Creative Videos")
    if mob_stats["top_videos"]:
        for i, video in enumerate(mob_stats["top_videos"]):
            st.write(f"**{i+1}. {video['title']}** - *{video['mob_name']}*")
            st.write(f"Creativity Score: {video['match_score']:.2f}")
            st.write("---")
    else:
        st.info("No videos available yet. Upload some videos to see the top performers!")
    
    # Campaign timeline
    st.subheader("Campaign Growth")
    
    # Generate dummy data for the timeline
    dates = pd.date_range(start="2025-01-01", periods=20, freq="D")
    cumulative_videos = [i*i for i in range(1, 21)]
    timeline_df = pd.DataFrame({
        "Date": dates,
        "Videos": cumulative_videos
    })
    
    fig = px.line(
        timeline_df, 
        x="Date", 
        y="Videos",
        title="Cumulative Campaign Growth"
    )
    st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.write("Powered by Twelve Labs Video Understanding API")