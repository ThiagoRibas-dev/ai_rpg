from app.database.db_manager import DBManager

DB_PATH = "ai_rpg.db"

def list_prompts():
    with DBManager(DB_PATH) as db:
        prompts = db.get_all_prompts()
        if not prompts:
            print("No prompts found in the database.")
            return

        print("Available Prompts:")
        for prompt in prompts:
            print(f"ID: {prompt.id}, Name: {prompt.name}")

if __name__ == "__main__":
    list_prompts()
