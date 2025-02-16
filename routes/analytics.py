import json
import os
from datetime import datetime
from flask import Blueprint, request, jsonify

# Create blueprint
bp = Blueprint('analytics', __name__)

# Ensure analytics directory exists
ANALYTICS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'analytics')
os.makedirs(ANALYTICS_DIR, exist_ok=True)

ANALYTICS_FILE = os.path.join(ANALYTICS_DIR, 'view_preferences.json')

def load_analytics():
    if not os.path.exists(ANALYTICS_FILE):
        return []
    try:
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_analytics(data):
    try:
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise Exception(f"Failed to save analytics: {str(e)}")

@bp.route("/view-preference", methods=['POST'])
def record_view_preference():
    try:
        data = request.get_json()
        analytics = load_analytics()
        
        # Add new entry
        analytics.append({
            "sessionId": data["sessionId"],
            "timestamp": data["timestamp"],
            "viewType": data["viewType"],
            "initialView": data["initialView"],
            "recorded_at": datetime.utcnow().isoformat()
        })
        
        save_analytics(analytics)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/view-preference/summary", methods=['GET'])
def get_view_preference_summary():
    try:
        analytics = load_analytics()
        
        if not analytics:
            return jsonify({
                "total_sessions": 0,
                "view_preferences": {"grid": 0, "table": 0},
                "conversion_rates": {"grid": 0, "table": 0}
            })
        
        # Count unique sessions
        unique_sessions = set(entry["sessionId"] for entry in analytics)
        total_sessions = len(unique_sessions)
        
        # Count view preferences
        view_counts = {"grid": 0, "table": 0}
        
        # Track which view users ended up using most
        session_final_views = {}
        for entry in analytics:
            session_id = entry["sessionId"]
            view_type = entry["viewType"]
            
            if session_id not in session_final_views:
                session_final_views[session_id] = {"grid": 0, "table": 0}
            
            session_final_views[session_id][view_type] += 1
        
        # Count which view was used most for each session
        for session_data in session_final_views.values():
            if session_data["grid"] > session_data["table"]:
                view_counts["grid"] += 1
            elif session_data["table"] > session_data["grid"]:
                view_counts["table"] += 1
        
        # Calculate conversion rates
        initial_views = {"grid": 0, "table": 0}
        stayed_with_initial = {"grid": 0, "table": 0}
        
        for session_id in unique_sessions:
            session_entries = [e for e in analytics if e["sessionId"] == session_id]
            if not session_entries:
                continue
                
            initial_view = session_entries[0]["initialView"]
            initial_views[initial_view] += 1
            
            # Check if they mostly used their initial view
            final_counts = session_final_views[session_id]
            if final_counts[initial_view] > final_counts["table" if initial_view == "grid" else "grid"]:
                stayed_with_initial[initial_view] += 1
        
        conversion_rates = {
            "grid": stayed_with_initial["grid"] / initial_views["grid"] if initial_views["grid"] > 0 else 0,
            "table": stayed_with_initial["table"] / initial_views["table"] if initial_views["table"] > 0 else 0
        }
        
        return jsonify({
            "total_sessions": total_sessions,
            "view_preferences": view_counts,
            "conversion_rates": conversion_rates
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
