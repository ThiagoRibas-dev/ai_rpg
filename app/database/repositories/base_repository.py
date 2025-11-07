'''Base repository for database operations.'''
import sqlite3
from typing import List, Optional

class BaseRepository:
    '''Base class for all repositories with common DB operations.'''
    
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
    
    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        '''Execute a query and return cursor.'''
        return self.conn.execute(query, params)
    
    def _fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        '''Execute and fetch one result.'''
        cursor = self._execute(query, params)
        return cursor.fetchone()
    
    def _fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        '''Execute and fetch all results.'''
        cursor = self._execute(query, params)
        return cursor.fetchall()
    
    def _commit(self):
        '''Commit transaction.'''
        self.conn.commit()