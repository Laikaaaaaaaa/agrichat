"""
Temporary configuration for testing the model setup
"""

def get_model_config():
    # Model configuration for free tier
    MODEL_CONFIG = {
        "model_ids": [
            "gemini",              # Basic free model
            "text-bison-001",      # Backup model
            "text-unicorn-001"     # Alternative model
        ],
        "generation_config": {
            "temperature": 0.7,
            "candidate_count": 1,
            "max_output_tokens": 50
        }
    }
    return MODEL_CONFIG