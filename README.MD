## Overview 

This solution enables a social media platform to automatically validate user-submitted videos showing creative milk drinking, categorize them into thematic "Milk Mobs," and create an engaging community experience.
The system uses Twelve Labs' AI video understanding capabilities to:

Detect if videos feature milk drinking activities
Assess the creativity of submissions
Classify valid videos into thematic "Milk Mobs" based on content
Find similar videos within each mob



## High-Level Architecture


MilkMob Analyzer
├── Backend Components
│   ├── VideoAnalyzer - Core integration with Twelve Labs APIs
│   ├── CampaignValidator - Validates videos meet campaign criteria
│   ├── MilkMobClassifier - Groups videos into thematic categories
│   └── CampaignTagDetector - Identifies campaign hashtags
├── Frontend Application
│   └── Streamlit UI - User interface with multiple tabs
└── Utilities
    └── Database - SQLite for storing mob assignments and stats


## Setup and Installation

1. **Clone the repository**

2. **Install dependencies**

pip install -r requirements.txt

3. **Create a .env file with your Twelve Labs API credentials**

Create a .env file with your Twelve Labs API credentials
TWELVE_LABS_API_KEY=your_api_key_here
TWELVE_LABS_INDEX_ID=milk_campaign_index

4. **Run the application**

streamlit run frontend/app.py


## How It Works

### Core Pipeline

1. **Upload & Tag Detection**: User uploads a video with caption, hashtags, and location.
2. **Video Analysis**: Twelve Labs SDK analyzes video content, detecting milk-related objects, drinking activities, and assessments of creativity.
3. **Campaign Validation**: The system validates if the video meets campaign criteria (shows milk drinking).
4. **Mob Classification**: Valid videos are classified into thematic "Milk Mobs" based on content.
5. **Content Exploration**: Users can explore other videos in their assigned mob.

### Data Flow Diagram

User Video → [Tag Detection] → [Twelve Labs Analysis] → [Campaign Validation] → [Mob Classification] → User Feedback
↓
[Dashboard/Analytics] ← [SQLite Database]



## Key Components in Detail

### 1. VideoAnalyzer (`backend/analyzer.py`)

This component handles interaction with the Twelve Labs API, including:
- Creating and managing video indexes
- Uploading and analyzing videos
- Searching for milk-related visual and audio content
- Generating summaries and creative assessments
- Finding similar videos through vector search

Key methods:
- `upload_and_analyze_video()`: Uploads video to Twelve Labs and performs comprehensive analysis
- `_perform_comprehensive_analysis()`: Analyzes visual and audio content using multiple search queries
- `find_similar_videos()`: Identifies similar videos using embedding similarity

### 2. CampaignValidator (`backend/validator.py`)

Validates if videos meet the campaign criteria:
- Checks for milk-related objects
- Verifies drinking activity
- Assesses creative elements
- Analyzes audio mentions of milk

Key methods:
- `validate_video()`: Main validation method that checks multiple criteria
- `_extract_confidence_from_text()`: Interprets text responses from the API

### 3. MilkMobClassifier (`backend/classifier.py`)

Classifies valid videos into thematic "Milk Mobs" such as:
- Active Milk Mob (sports/fitness)
- Dance Milk Mob (creative dancers)
- Chef Milk Mob (culinary creations)
- Comedy Milk Mob (humor)
- Art Milk Mob (artistic expressions)
- Science Milk Mob (experiments)
- Extreme Milk Mob (challenges)

Key methods:
- `classify_video()`: Assigns video to appropriate mob
- `get_all_mobs()`: Returns information about all mobs
- `get_mob_stats()`: Provides statistics about mobs

The classifier uses a SQLite database to store mob assignments and statistics.

### 4. CampaignTagDetector (`backend/tag_detector.py`)

Detects campaign-related hashtags in post content:
- Identifies campaign tags like #gotmilk, #milkmob
- Extracts metadata from posts
- Tracks popularity of different tags

Key methods:
- `detect_tags()`: Identifies campaign tags in post data
- `get_popular_tags()`: Returns most popular tags with counts

### 5. Frontend Application (`frontend/app.py`)

Built with Streamlit, featuring three tabs:
- **Upload & Validate**: For submitting videos
- **Explore Milk Mobs**: Explore thematic categories
- **Dashboard**: Campaign analytics and statistics

## Example Usage

### Uploading a Video:
1. Navigate to the "Upload & Validate" tab
2. Upload a video featuring someone drinking milk creatively
3. Add caption, hashtags (like #gotmilk or #milkmob), and location info
4. Click "Process Video"
5. If validated, the system assigns the video to a Milk Mob
6. Share the result with a generated link

### Exploring Mobs:
1. Go to the "Explore Milk Mobs" tab
2. Browse different Milk Mob categories
3. View sample videos and keywords for each mob
4. Click "Join" on a mob you want to participate in




## API Usage Notes

### Twelve Labs SDK

The solution leverages several Twelve Labs API capabilities:
- `task.create`: For uploading and indexing videos
- `search.query`: For finding milk-related content
- `generate.summarize`: For generating video summaries
- `generate.text`: For creative assessment and semantic analysis
- `search.vector`: For finding similar videos



## Dependencies

- streamlit: For the user interface
- twelvelabs: Twelve Labs SDK for video understanding
- python-dotenv: For environment variables
- pandas & plotly: For data visualization
- sqlite3: For database operations


