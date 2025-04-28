
## Milestone 1 Report

### A/B Testing (`/api/analytics`)

The backend implements A/B testing functionality to track and analyze user preferences between different view types (grid vs. table view).

Note: There was no specific instructions on what to include in Milestone 1, so we included the README.md file below. Note, we were at a pretty intense sprint before an accelerator application, so we focused on integrating this milestone and doing work that is directly related to our product. For a full view of our code, here it is:

https://github.com/Neotix-Dev/neotix-backend/commit/088d1d58646ed493f89774682e4d72bb600e461a#diff-0445c1363182333eb5fcb39bcfe8424624db4fe53805d34c7c3346f994c140e7L1-L144

#### View Preference Tracking
- `POST /view-preference` - Record user view preference
  - Required payload:
    ```json
    {
      "sessionId": "unique_session_id",
      "timestamp": "ISO timestamp",
      "viewType": "grid|table",
      "initialView": "grid|table"
    }
    ```

#### Analytics
- `GET /view-preference/summary` - Get summary of view preferences
  - Returns:
    ```json
    {
      "total_sessions": "number of unique sessions",
      "view_preferences": {
        "grid": "number of users who preferred grid view",
        "table": "number of users who preferred table view"
      },
      "conversion_rates": {
        "grid": "percentage who stayed with grid view",
        "table": "percentage who stayed with table view"
      }
    }
    ```

#### Implementation Details
- Users are randomly assigned either grid or table view on their first visit
- The system tracks:
  - Initial view type assigned
  - View type changes during the session
  - Final view type preference
- Analytics are stored in JSON format at `data/analytics/view_preferences.json`

#### Setup Instructions
1. Ensure the `data/analytics` directory exists:
   ```bash
   mkdir -p data/analytics
   ```
2. Initialize the analytics file:
   ```bash
   echo "[]" > data/analytics/view_preferences.json
   ```
3. Ensure write permissions:
   ```bash
   chmod 644 data/analytics/view_preferences.json
   ```
All the analytics data is stored in `data/analytics/view_preferences.json`.
