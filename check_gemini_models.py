import os
import google.generativeai as genai

# Make sure GEMINI_API_KEY is set in the same terminal before running:
# export GEMINI_API_KEY="YOUR_KEY"

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Listing available models for this API key:\n")
for m in genai.list_models():
    # Only show text-capable models
    if "generateContent" in m.supported_generation_methods:
        print("-", m.name)
