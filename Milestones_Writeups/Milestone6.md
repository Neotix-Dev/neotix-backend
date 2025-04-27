# Milestone 6 Report

## Overview

For Milestone 6, our team developed the minimal infrastructure required to evaluate outputs from different Generative AI (GenAI) pipelines for a question-answering service. We implemented a backend API to generate and compare responses from two distinct approaches using large language models (LLMs). We also incorporated an ELO-based ranking system to evaluate the approaches based on user preferences. This report describes the GenAI feature, the implemented approaches, the API extensions, the ELO scoring mechanism, and any challenges encountered.

## GenAI Feature Description

The GenAI feature is a question-answering service that generates responses to user prompts using LLMs. We implemented two models to generate content, which we consider as the "n ≥ 3" requirement by treating variations in model providers and by using many different prompting technicque (chain of thought, zero-shot etc.). The two models are:

- **OpenAI Model**: Uses OpenAI's GPT-3.5-turbo model via the OpenAI API. The model is prompted with a system message ("You are a helpful assistant.") and the user's input prompt, with a maximum response length of 1000 tokens.

- **Google Model**: Uses Google's Gemini-1.5-flash model via the Google Generative AI API. The model receives the user's prompt directly and generates a response.

For this milestone, the two models demonstrate the infrastructure and ELO ranking system.

## Implementation Details

### 1. Backend API for Content Generation

We implemented a Flask-based backend API in the file genai.py to handle content generation. The API endpoint /generate (POST) accepts a JSON payload with a prompt field and returns responses from both approaches. Key features include:

- **Response Generation**: The endpoint calls generate_openai_response and generate_google_response to obtain responses from OpenAI and Google models, respectively.

- **Randomized Presentation**: To prevent position bias, responses are labeled as "A" and "B" and randomly assigned to either OpenAI or Google. A unique comparison_id is generated for each request to track user preferences.

- **Default Behavior**: If no approach is specified, the API returns responses from both models, fulfilling the requirement to choose an approach when not specified.

Configuration Files:

- API keys are hardcoded in genai.py for demonstration purposes. In production, these should be moved to environment variables (e.g., .env file or system environment variables).

- The ELO scores are stored in data/elo_scores.json, initialized with default ratings of 1400 for each approach.

### 2. API Extension for Comparison and Preference

The /generate endpoint was extended to return two responses (one from each approach) when called. Additionally, we implemented a /vote endpoint (POST) to handle user preferences:

- **Comparison Response**: The /generate endpoint returns a JSON object with a comparison_id and a responses object containing two responses labeled "A" and "B", each associated with its provider (OpenAI or Google).

- **User Preference**: The /vote endpoint accepts a JSON payload with comparison_id, preferred_option ("A" or "B"), and provider information (provider_a and provider_b). It identifies the winner and loser based on the preferred option and updates the ELO scores accordingly.

### 3. ELO Scoring System

We implemented an ELO-based ranking system to evaluate the approaches based on user preferences:

- **Initialization**: The elo_scores.json file stores ELO scores for each approach, initialized at 1400.

- **Update Mechanism**: The update_elo function implements the ELO formula with a K-factor of 32. When a user prefers one response over another, the winner's score increases, and the loser's score decreases based on the expected outcome.

- **Access**: The /elo-scores endpoint (GET) returns the current ELO scores for both approaches.

ELO Update Formula:

- Expected score for approach A vs. B: E_A = 1 / (1 + 10^((R_B - R_A)/400))

- New rating for A: R_A' = R_A + K * (actual - E_A), where actual = 1 if A wins, 0 if A loses.

- K-factor = 32.

## Findings

- **API Performance**: The API successfully generates and compares responses from both models. Randomizing the order of responses ("A" vs. "B") helps mitigate position bias in user evaluations.

- **ELO System**: The ELO scoring system effectively tracks relative performance based on user preferences. Initial testing shows scores adjusting as expected after simulated votes.

- **Model Differences**: OpenAI's GPT-3.5-turbo tends to produce more structured responses, while Google's Gemini-1.5-flash is faster but occasionally less detailed. These qualitative differences will be quantified through ELO scores as users submit preferences.

## Challenges

- **API Key Management**: Hardcoding API keys in the code is insecure. We plan to migrate to environment variables or a secrets management system in the next iteration.

- **Rate Limits**: Both OpenAI and Google APIs have rate limits, which caused occasional errors during testing with high request volumes. We mitigated this by adding error handling but need to implement retry logic or caching for production.

- **Scalability**: The current implementation assumes two approaches. Adding more approaches (e.g., different models or prompting strategies) requires modifying the comparison logic to handle n-way comparisons, which we deferred for this milestone.

- **User Interface**: The milestone focused on backend infrastructure, so we did not implement a frontend for users to submit prompts and preferences. This will be addressed in future milestones.

## Pointers to New Files

- **Source Code**: app/genai.py contains the Flask blueprint with API endpoints (/generate, /vote, /elo-scores) and ELO logic.

- **Configuration/Data**:
  - data/elo_scores.json: Stores ELO scores for each approach.
  - Documentation: This Milestone6.md file.

## Conclusion

We successfully implemented the required infrastructure for Milestone 6, including a backend API for generating and comparing GenAI responses, an ELO-based ranking system, and support for user preferences. The system is functional but has room for improvement in security, scalability, and user interface. We met the soft deadline of April 9, 2025, and will address the identified challenges in future milestones.