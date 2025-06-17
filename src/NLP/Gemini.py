from dotenv import load_dotenv
import os
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("API_KEY_GEMINI")

class Gemini():
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        genai.configure(api_key=api_key)

    def ask(self, prompt: str):
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        return response.text

if __name__ == "__main__":
    gemini = Gemini()
    response = gemini.ask("Who is Abel Ponce Gonzales?")
    print(response)
