import os
import json

def load_json(file_path):
    if not os.path.exists(file_path):   return {}
    
    with open(file_path, 'r') as file:
        return json.load(file)
    
def save_json(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)