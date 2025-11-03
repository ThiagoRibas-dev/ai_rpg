from app.database.db_manager import DBManager

DB_PATH = "ai_rpg.db"

def get_prompt_content(prompt_id: int):
    with DBManager(DB_PATH) as db:
        prompt = db.get_prompt_by_id(prompt_id) # Assuming get_prompt_by_id exists or will be added
        if prompt:
            print(f"Content of Prompt ID {prompt_id} (Name: {prompt.name}):\n{prompt.content}")
        else:
            print(f"Prompt with ID {prompt_id} not found.")

if __name__ == "__main__":
    # For now, we'll just print a message that this function needs to be called with an ID
    print("This script needs to be called with a prompt ID. For example: python get_prompt_content.py 1")
