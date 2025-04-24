from flask import Blueprint, jsonify, request
import os
import json
import openai
import google.generativeai as genai
from datetime import datetime
import random

bp = Blueprint('genai', __name__)

# IMPORTANT: In production, these should be set as environment variables
# These are hardcoded here for demonstration purposes only
OPENAI_API_KEY = "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"
GOOGLE_API_KEY = "AIzaSyDaUurPijhXcl-nqu4SvRbC1sqX8dciWxY"

# Configure API clients
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GOOGLE_API_KEY)

# File to store ELO scores
ELO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'elo_scores.json')

# Ensure data directory exists
os.makedirs(os.path.dirname(ELO_FILE), exist_ok=True)

# ELO rating system constants
K_FACTOR = 32  # How much a single match affects ratings
DEFAULT_RATING = 1400  # Starting ELO score

def load_elo_scores():
    """Load ELO scores from file or create if not exists"""
    if not os.path.exists(ELO_FILE):
        # Initialize with default ratings
        default_scores = {
            "openai": DEFAULT_RATING,
            "google": DEFAULT_RATING
        }
        # Save the default scores
        with open(ELO_FILE, 'w') as f:
            json.dump(default_scores, f, indent=2)
        return default_scores
    
    # Load existing scores
    try:
        with open(ELO_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # Handle corrupted file or other issues
        default_scores = {
            "openai": DEFAULT_RATING,
            "google": DEFAULT_RATING
        }
        with open(ELO_FILE, 'w') as f:
            json.dump(default_scores, f, indent=2)
        return default_scores

def save_elo_scores(scores):
    """Save ELO scores to file"""
    with open(ELO_FILE, 'w') as f:
        json.dump(scores, f, indent=2)

def update_elo(winner, loser):
    """Update ELO scores based on match outcome"""
    scores = load_elo_scores()
    
    # Extract current ratings
    rating_winner = scores[winner]
    rating_loser = scores[loser]
    
    # Calculate expected scores
    expected_winner = 1 / (1 + 10 ** ((rating_loser - rating_winner) / 400))
    expected_loser = 1 / (1 + 10 ** ((rating_winner - rating_loser) / 400))
    
    # Update ratings
    scores[winner] = rating_winner + K_FACTOR * (1 - expected_winner)
    scores[loser] = rating_loser + K_FACTOR * (0 - expected_loser)
    
    # Save updated scores
    save_elo_scores(scores)
    return scores

def generate_openai_response(prompt):
    """Generate a response using OpenAI's API"""
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating OpenAI response: {str(e)}"

def generate_google_response(prompt):
    """Generate a response using Google's Gemini API"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating Google response: {str(e)}"

@bp.route('/generate', methods=['POST'])
def generate_responses():
    """Generate responses from both models"""
    data = request.get_json()
    
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing prompt in request"}), 400
    
    prompt = data['prompt']
    
    # Generate responses from both models
    openai_response = generate_openai_response(prompt)
    google_response = generate_google_response(prompt)
    
    # Generate unique ID for this comparison
    comparison_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    
    # Randomly determine the order to prevent position bias
    if random.choice([True, False]):
        response = {
            "comparison_id": comparison_id,
            "responses": {
                "A": {"provider": "openai", "text": openai_response},
                "B": {"provider": "google", "text": google_response}
            }
        }
    else:
        response = {
            "comparison_id": comparison_id,
            "responses": {
                "A": {"provider": "google", "text": google_response},
                "B": {"provider": "openai", "text": openai_response}
            }
        }
    
    return jsonify(response), 200

@bp.route('/vote', methods=['POST'])
def submit_preference():
    """Submit user preference between two model outputs"""
    data = request.get_json()
    
    required_fields = ['comparison_id', 'preferred_option']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    comparison_id = data['comparison_id']
    preferred = data['preferred_option']  # 'A' or 'B'
    
    # Get provider information from request
    provider_a = data.get('provider_a')
    provider_b = data.get('provider_b')
    
    if not provider_a or not provider_b:
        return jsonify({"error": "Missing provider information"}), 400
    
    # Determine winner and loser
    winner = provider_a if preferred == 'A' else provider_b
    loser = provider_b if preferred == 'A' else provider_a
    
    # Update ELO scores
    updated_scores = update_elo(winner, loser)
    
    return jsonify({
        "message": "Preference recorded successfully",
        "updated_elo_scores": updated_scores
    }), 200

@bp.route('/elo-scores', methods=['GET'])
def get_elo_scores():
    """Get current ELO scores for both models"""
    scores = load_elo_scores()
    return jsonify(scores), 200