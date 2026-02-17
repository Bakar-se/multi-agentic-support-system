"""Quick script to list available Gemini models."""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("Installing google-generativeai...")
    import subprocess
    subprocess.check_call(["pip", "install", "google-generativeai"])
    import google.generativeai as genai

google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    print("ERROR: GOOGLE_API_KEY not set in .env file")
    exit(1)

genai.configure(api_key=google_api_key)

print("Fetching available models...\n")

try:
    models = genai.list_models()
    
    print("Available models that support generateContent:\n")
    generate_content_models = []
    
    for model in models:
        name = model.name
        description = getattr(model, 'display_name', '') or getattr(model, 'description', '')
        supported_methods = getattr(model, 'supported_generation_methods', [])
        
        if 'generateContent' in supported_methods:
            generate_content_models.append(name)
            print(f"✅ {name}")
            if description:
                print(f"   Description: {description}")
            print()
    
    if generate_content_models:
        print("\n" + "="*80)
        print("RECOMMENDED MODEL NAMES FOR USE IN CODE:")
        print("="*80)
        
        # Extract model names without "models/" prefix for LangChain
        for model_name in generate_content_models:
            # Remove "models/" prefix if present
            clean_name = model_name.replace("models/", "")
            print(f'  "{clean_name}"')
        
        # Suggest the best one (prefer flash for free tier)
        best_model = None
        for model_name in generate_content_models:
            if "flash" in model_name.lower():
                best_model = model_name.replace("models/", "")
                break
        if not best_model and generate_content_models:
            best_model = generate_content_models[0].replace("models/", "")
        
        if best_model:
            print(f"\n💡 Recommended for free tier: \"{best_model}\"")
    else:
        print("❌ No models found that support generateContent")
        
except Exception as e:
    print(f"❌ Error listing models: {e}")
    import traceback
    traceback.print_exc()

