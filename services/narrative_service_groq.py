import os
try:
    from groq import Groq
except ImportError:
    Groq = None

class NarrativeServiceGroq:
    def __init__(self, api_key=None):
        self.groq_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.groq_key:
            raise ValueError("API key for Groq is missing.")
        if not Groq:
            raise ImportError("Groq library not installed.")
        self.client = Groq(api_key=self.groq_key)
        self.model = "llama-3.3-70b-versatile" # Latest Supported Model
        self.history = []
        self.system_instruction = (
            "You are the Game Master (GM) for a tabletop roleplaying game campaign. "
            "Your role is to describe the world, react to player actions, and play all NPCs. "
            "Be descriptive, fair, and engaging. "
            "Identify the player speaking by their name provided in the prompt. "
            "VISUALS: If you describe a new location, scene, or battle map, specifically include the keyword [GENERATE_MAP] at the very end of your response."
        )

    def generate_response(self, char_name, prompt, rules_context=""):
        # Construct messages
        messages = [
            {"role": "system", "content": self.system_instruction + f"\nContext: {rules_context}"},
        ]
        # addict history
        for msg in self.history:
            messages.append(msg)
        
        # Add current user prompt
        user_msg = {"role": "user", "content": f"{char_name}: {prompt}"}
        messages.append(user_msg)

        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=1024,
            )
            response_text = chat_completion.choices[0].message.content
            
            # Update history
            self.history.append(user_msg)
            self.history.append({"role": "assistant", "content": response_text})
            
            return response_text
        except Exception as e:
            return f"Groq Error: {e}"
