'''Repository for session operations.'''
from typing import List, Optional
from app.models.game_session import GameSession
from .base_repository import BaseRepository

class SessionRepository(BaseRepository):
    '''Handles all session-related database operations.'''
    
    def create(self, name: str, session_data: str, prompt_id: int) -> GameSession:
        '''Create a new game session.'''
        cursor = self._execute(
            '''INSERT INTO sessions 
               (name, session_data, prompt_id, memory, authors_note, game_mode) 
               VALUES (?, ?, ?, '', '', 'SETUP')''',
            (name, session_data, prompt_id)
        )
        self._commit()
        return GameSession(
            id=cursor.lastrowid,
            name=name,
            session_data=session_data,
            prompt_id=prompt_id,
            memory="",
            authors_note="",
            game_mode="SETUP"
        )
    
    def get_by_id(self, session_id: int) -> Optional[GameSession]:
        '''Load a session by ID.'''
        row = self._fetchone(
            '''SELECT id, name, session_data, prompt_id, memory, authors_note, 
                      game_time, game_mode 
               FROM sessions WHERE id = ?''',
            (session_id,)
        )
        if row:
            return GameSession(**dict(row))
        return None
    
    def get_all(self) -> List[GameSession]:
        '''Get all sessions.'''
        rows = self._fetchall(
            '''SELECT id, name, session_data, prompt_id, memory, authors_note, 
                      game_time, game_mode 
               FROM sessions'''
        )
        return [GameSession(**dict(row)) for row in rows]
    
    def get_by_prompt(self, prompt_id: int) -> List[GameSession]:
        '''Get all sessions for a specific prompt.'''
        rows = self._fetchall(
            '''SELECT id, name, session_data, prompt_id, memory, authors_note, 
                      game_time, game_mode 
               FROM sessions WHERE prompt_id = ?''',
            (prompt_id,)
        )
        return [GameSession(**dict(row)) for row in rows]
    
    def update(self, session: GameSession):
        '''Update a session.'''
        self._execute(
            '''UPDATE sessions 
               SET name = ?, session_data = ?, prompt_id = ?, memory = ?, 
                   authors_note = ?, game_time = ?, game_mode = ? 
               WHERE id = ?''',
            (session.name, session.session_data, session.prompt_id, 
             session.memory, session.authors_note, session.game_time, 
             session.game_mode, session.id)
        )
        self._commit()
    
    def update_context(self, session_id: int, memory: str, authors_note: str):
        '''Update only the context fields.'''
        self._execute(
            "UPDATE sessions SET memory = ?, authors_note = ? WHERE id = ?",
            (memory, authors_note, session_id)
        )
        self._commit()
    
    def update_game_time(self, session_id: int, game_time: str):
        '''Update only the game_time field.'''
        self._execute(
            "UPDATE sessions SET game_time = ? WHERE id = ?",
            (game_time, session_id)
        )
        self._commit()
    
    def get_context(self, session_id: int) -> Optional[dict]:
        '''Get context fields for a session.'''
        row = self._fetchone(
            "SELECT memory, authors_note FROM sessions WHERE id = ?",
            (session_id,)
        )
        if row:
            return {"memory": row["memory"] or "", "authors_note": row["authors_note"] or ""}
        return None