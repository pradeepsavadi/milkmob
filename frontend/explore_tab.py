import streamlit as st
import os
import sys
import sqlite3
import base64
from pathlib import Path

# Import the MilkMob classifier
from backend import MilkMobClassifier

def render_video_card(video, key_prefix):
    """Render a single video card"""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Show thumbnail
        if video.get('thumbnail_path') and os.path.exists(video['thumbnail_path']):
            st.image(video['thumbnail_path'], use_column_width=True)
        else:
            # Fallback to a colored placeholder
            st.markdown(
                f"""
                <div style="background-color:#2196F3; height:120px; 
                border-radius:5px; display:flex; align-items:center; justify-content:center; color:white;">
                <span style="font-size:36px;">🎬</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
    
    with col2:
        # Show video details
        st.markdown(f"**{video.get('title', 'Untitled Video')}**")
        
        if video.get('description'):
            st.markdown(video['description'][:100] + ('...' if len(video['description']) > 100 else ''))
        
        if video.get('location'):
            st.markdown(f"📍 {video['location']}")
        
        # Display match score
        score = video.get('match_score', 0.5)
        st.progress(score, text=f"Match: {score:.0%}")
        
        # Video player button
        if video.get('video_path') and os.path.exists(video['video_path']):
            if st.button("▶️ Play Video", key=f"{key_prefix}_play_{video['video_id']}"):
                st.video(video['video_path'])

def explore_milk_mobs():
    """Render the enhanced Explore Milk Mobs tab"""
    st.title("🥛 Explore Milk Mobs")
    st.write("Learn about the different Milk Mobs you can join with your creative milk videos!")
    
    # Initialize the classifier
    classifier = MilkMobClassifier()
    
    # Get all mob data
    all_mobs = classifier.get_all_mobs()
    
    # Add search functionality
    search = st.text_input("🔍 Search for mobs or videos", placeholder="Enter keywords...")
    
    # Add view options
    view_mode = st.radio("View mode:", ("Compact", "Detailed"), horizontal=True)
    
    # Show mobs
    if view_mode == "Compact":
        # Compact view - show mobs in a grid
        col1, col2 = st.columns(2)
        
        for i, mob in enumerate(all_mobs):
            with col1 if i % 2 == 0 else col2:
                # Check if search matches
                if search and search.lower() not in mob['name'].lower() and search.lower() not in mob['description'].lower():
                    if not any(search.lower() in kw.lower() for kw in mob['sample_keywords']):
                        continue
                
                # Create styled expander with color theme
                with st.expander(f"{mob['icon']} {mob['name']} ({mob['video_count']} videos)"):
                    st.markdown(
                        f"""
                        <div style="border-left: 5px solid {mob['color_theme']}; padding-left: 10px;">
                            {mob['description']}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    # Show keywords
                    if mob['sample_keywords']:
                        st.markdown("**Keywords:**")
                        keyword_html = " ".join([f'<span style="background-color:{mob["color_theme"]}30; padding:3px 8px; border-radius:10px; margin-right:5px;">{kw}</span>' for kw in mob['sample_keywords']])
                        st.markdown(f"<div style='margin-bottom:10px;'>{keyword_html}</div>", unsafe_allow_html=True)
                    
                    # Show videos if any
                    if mob['sample_videos']:
                        st.markdown("**Featured Videos:**")
                        for j, video in enumerate(mob['sample_videos']):
                            # Check if search matches video title/description
                            if search and video.get('title') and search.lower() not in video['title'].lower():
                                if not (video.get('description') and search.lower() in video['description'].lower()):
                                    continue
                            
                            st.markdown("---")
                            render_video_card(video, f"compact_{mob['mob_id']}_{j}")
                    else:
                        st.info("No videos in this mob yet. Be the first to join!")
                    
                    # Join button
                    st.button("Join This Mob", key=f"join_{mob['mob_id']}", 
                              help="Upload your creative milk video to join this mob!")
    else:
        # Detailed view - show each mob in full width
        for i, mob in enumerate(all_mobs):
            # Check if search matches
            if search and search.lower() not in mob['name'].lower() and search.lower() not in mob['description'].lower():
                if not any(search.lower() in kw.lower() for kw in mob['sample_keywords']):
                    continue
            
            # Create styled header with color theme
            st.markdown(
                f"""
                <div style="background-color:{mob['color_theme']}15; padding:15px; 
                     border-radius:10px; border-left:5px solid {mob['color_theme']}; margin-bottom:20px;">
                    <h3>{mob['icon']} {mob['name']} ({mob['video_count']} videos)</h3>
                    <p>{mob['description']}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Keywords section
            if mob['sample_keywords']:
                st.markdown("**Keywords:**")
                keyword_html = " ".join([f'<span style="background-color:{mob["color_theme"]}30; padding:3px 8px; border-radius:10px; margin-right:5px;">{kw}</span>' for kw in mob['sample_keywords']])
                st.markdown(f"<div style='margin-bottom:20px;'>{keyword_html}</div>", unsafe_allow_html=True)
            
            # Videos section
            if mob['sample_videos']:
                st.markdown("### Featured Videos")
                
                # Create columns for videos
                cols = st.columns(min(3, len(mob['sample_videos'])))
                
                for j, video in enumerate(mob['sample_videos']):
                    # Check if search matches video title/description
                    if search and video.get('title') and search.lower() not in video['title'].lower():
                        if not (video.get('description') and search.lower() in video['description'].lower()):
                            continue
                    
                    with cols[j % len(cols)]:
                        # Thumbnail
                        if video.get('thumbnail_path') and os.path.exists(video['thumbnail_path']):
                            st.image(video['thumbnail_path'], use_column_width=True)
                        else:
                            # Fallback to a colored placeholder
                            st.markdown(
                                f"""
                                <div style="background-color:{mob["color_theme"]}; height:120px; 
                                border-radius:5px; display:flex; align-items:center; justify-content:center; color:white;">
                                <span style="font-size:36px;">🎬</span>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                        
                        # Title
                        st.markdown(f"**{video.get('title', 'Untitled Video')}**")
                        
                        # Video player button
                        if video.get('video_path') and os.path.exists(video['video_path']):
                            if st.button("▶️ Play", key=f"detailed_{mob['mob_id']}_{j}"):
                                st.video(video['video_path'])
                        
                        # Match score
                        score = video.get('match_score', 0.5)
                        st.progress(score, text=f"Match: {score:.0%}")
            else:
                st.info("No videos in this mob yet. Be the first to join!")
            
            # Join button
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                st.button(f"Join {mob['name']}", key=f"join_detailed_{mob['mob_id']}",
                          help="Upload your creative milk video to join this mob!")
            
            st.markdown("---")
    
    # Add footer
    st.markdown("### Ready to join a Milk Mob?")
    st.write("Upload your creative milk-drinking video in the Upload & Validate tab to join one of these exciting communities!")

if __name__ == "__main__":
    # Test the function
    explore_milk_mobs()