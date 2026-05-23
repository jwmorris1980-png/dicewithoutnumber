import os

class MemoryService:
    def __init__(self, data_dir="data", filename="house_rules.txt"):
        self.data_dir = data_dir
        self.filepath = os.path.join(data_dir, filename)
        
        # Ensure dir exists
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        # Ensure file exists
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                f.write("--- HOUSE RULES & NOTES ---\n")

    def remember(self, text):
        """Appends a rule to the persistent memory."""
        try:
            with open(self.filepath, 'a') as f:
                f.write(f"- {text}\n")
            return True
        except Exception as e:
            print(f"Memory Write Error: {e}")
            return False

    def get_memory(self):
        """Reads all house rules."""
        try:
            with open(self.filepath, 'r') as f:
                return f.read()
        except Exception as e:
            return ""

    def clear(self):
        """Wipes the rules file."""
        with open(self.filepath, 'w') as f:
            f.write("--- HOUSE RULES & NOTES ---\n")
