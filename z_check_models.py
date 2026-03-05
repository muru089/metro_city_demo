import google.generativeai as genai

# Replace with your actual API key from the "Get API key" section in Studio
genai.configure(api_key="AIzaSyClwEFvNZPnIXUzJskirS8XTHXLpc6R-Jo")

print("Listing models you can access:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Model Name: {m.name}")