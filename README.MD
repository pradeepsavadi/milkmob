# MilkMob - Video Campaign Platform

MilkMob is a prototype social media tool that automatically validates and categorizes creative milk drinking videos using the Twelve Labs video understanding API. It groups content into themed "Milk Mobs" to encourage community engagement.

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [How It Works](#how-it-works)
- [Key Components](#key-components)
- [Example Usage](#example-usage)
- [API Usage Notes](#api-usage-notes)
- [Dependencies](#dependencies)
- [Contributing](#contributing)

## Overview
This solution enables a social media platform to automatically validate user-submitted videos showing creative milk drinking, categorize them into thematic "Milk Mobs," and create an engaging community experience. It relies on Twelve Labs' AI video understanding capabilities to:
- Detect milk-drinking activities
- Assess the creativity of submissions
- Classify valid videos into thematic mobs based on content
- Find similar videos within each mob

## Project Structure
```
backend/    # Core business logic and API integrations
frontend/   # Streamlit app for interacting with the system
requirements.txt
milk_mobs.db  # SQLite database (created automatically)
```
Major backend modules include:
- **VideoAnalyzer** (`backend/analyzer.py`) – Interfaces with Twelve Labs APIs
- **CampaignValidator** (`backend/validator.py`) – Validates that a video fits campaign criteria
- **MilkMobClassifier** (`backend/classifier.py`) – Groups validated videos into themed mobs
- **CampaignTagDetector** (`backend/tag_detector.py`) – Detects campaign hashtags

## Prerequisites
- Python 3.9 or newer
- Twelve Labs account and API key
- Optional: `ffmpeg` for enhanced video processing

## Installation
1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd milkmob
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set environment variables**
   Create a `.env` file with your Twelve Labs credentials:
   ```
   TWELVE_LABS_API_KEY=your_api_key
   TWELVE_LABS_INDEX_ID=milk_campaign_index
   ```
 
## Database Migration
If you used a previous version of MilkMob, your `milk_mobs.db` may lack new columns. Run `python backend/migrate_db.py` to upgrade the schema or delete the old file to let the app recreate it.

## Running the App
Start the Streamlit application from the project root:
```bash
streamlit run frontend/app.py
```
The UI provides tabs for uploading videos, exploring mobs, and viewing dashboard analytics.

## How It Works
1. **Upload & Tag Detection** – Users upload a video with caption and hashtags.
2. **Video Analysis** – The Twelve Labs SDK analyzes the content for milk-drinking activity and creative elements.
3. **Campaign Validation** – Videos that meet campaign rules are marked valid.
4. **Mob Classification** – Valid content is organized into a themed Milk Mob.
5. **Content Exploration** – Users browse their mob and discover similar videos.

## Key Components
- **VideoAnalyzer** – Uploads and analyzes videos with Twelve Labs.
- **CampaignValidator** – Checks that videos meet required criteria.
- **MilkMobClassifier** – Assigns videos to themed mobs and stores results in SQLite.
- **CampaignTagDetector** – Extracts and tracks campaign hashtags.
- **Streamlit Frontend** – Presents an easy-to-use interface.

## Example Usage
### Uploading a Video
1. Open the **Upload & Validate** tab.
2. Select a creative video of milk drinking.
3. Add a caption, hashtags such as `#gotmilk` or `#milkmob`, and location info.
4. Click **Process Video**. If validated, the app assigns it to a mob and displays related videos.

### Exploring Mobs
1. Navigate to the **Explore Milk Mobs** tab.
2. Browse mob categories, example videos, and keywords.
3. Join a mob to participate and share similar content.

## API Usage Notes
The app leverages several Twelve Labs API endpoints:
- `task.create` – Upload and index videos
- `search.query` – Find milk-related visual or audio content
- `generate.summarize` – Produce video summaries
- `generate.text` – Assess creativity semantically
- `search.vector` – Locate similar videos with embeddings
- `generate.caption` *(optional)* – Generate short captions
- `generate.storyboard` *(optional)* – Retrieve storyboard frames

When optional endpoints are enabled, the Streamlit app shows the generated caption and storyboard inside the **Twelve Labs API Analysis** section.

## Dependencies
- `streamlit` – Web app framework
- `twelvelabs` – Twelve Labs SDK
- `python-dotenv` – Environment variable loading
- `pandas` & `plotly` – Data visualization
- `sqlite3` – Database operations

## Contributing
Contributions are welcome! Feel free to open issues or pull requests to extend functionality, improve documentation, or report bugs.

