'''Repository for prompt operations.'''
from typing import List
from app.models.prompt import Prompt
from .base_repository import BaseRepository

class PromptRepository(BaseRepository):
    '''Handles all prompt-related database operations.'''
    
    def create(self, name: str, content: str, initial_message: str = "") -> Prompt:
        '''Create a new prompt.'''
        cursor = self._execute(
            "INSERT INTO prompts (name, content, initial_message) VALUES (?, ?, ?)",
            (name, content, initial_message)
        )
        self._commit()
        return Prompt(id=cursor.lastrowid, name=name, content=content, initial_message=initial_message)
    
    def get_all(self) -> List[Prompt]:
        '''Get all prompts.'''
        rows = self._fetchall("SELECT id, name, content, initial_message FROM prompts")
        return [Prompt(**dict(row)) for row in rows]
    
    def get_by_id(self, prompt_id: int) -> Prompt | None:
        '''Get a prompt by ID.'''
        row = self._fetchone(
            "SELECT id, name, content, initial_message FROM prompts WHERE id = ?",
            (prompt_id,)
        )
        return Prompt(**dict(row)) if row else None
    
    def update(self, prompt: Prompt):
        '''Update a prompt.'''
        self._execute(
            "UPDATE prompts SET name = ?, content = ?, initial_message = ? WHERE id = ?",
            (prompt.name, prompt.content, prompt.initial_message, prompt.id)
        )
        self._commit()
    
    def delete(self, prompt_id: int):
        '''Delete a prompt.'''
        self._execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        self._commit()