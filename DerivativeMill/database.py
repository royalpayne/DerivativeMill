"""
Database Abstraction Layer for DerivativeMill
Supports both SQLite (local) and PostgreSQL (multi-user sync)
"""

import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from abc import ABC, abstractmethod

# Try to import psycopg2 for PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseBackend(ABC):
    """Abstract base class for database backends"""
    
    @abstractmethod
    def connect(self):
        """Return a database connection"""
        pass
    
    @abstractmethod
    def get_placeholder(self):
        """Return the parameter placeholder (? for SQLite, %s for PostgreSQL)"""
        pass
    
    @abstractmethod
    def init_schema(self):
        """Initialize the database schema"""
        pass


class SQLiteBackend(DatabaseBackend):
    """SQLite database backend for local/single-user operation"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
    def connect(self):
        return sqlite3.connect(str(self.db_path))
    
    def get_placeholder(self):
        return "?"
    
    def init_schema(self):
        conn = self.connect()
        c = conn.cursor()
        
        c.execute("""CREATE TABLE IF NOT EXISTS parts_master (
            part_number TEXT PRIMARY KEY,
            description TEXT,
            hts_code TEXT,
            country_origin TEXT,
            mid TEXT,
            client_code TEXT,
            steel_ratio REAL DEFAULT 1.0,
            non_steel_ratio REAL DEFAULT 0.0,
            last_updated TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS tariff_232 (
            hts_code TEXT PRIMARY KEY,
            material TEXT,
            classification TEXT,
            chapter TEXT,
            chapter_description TEXT,
            declaration_required TEXT,
            notes TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS sec_232_actions (
            tariff_no TEXT PRIMARY KEY,
            action TEXT,
            description TEXT,
            advalorem_rate TEXT,
            effective_date TEXT,
            expiration_date TEXT,
            specific_rate TEXT,
            additional_declaration TEXT,
            note TEXT,
            link TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS mapping_profiles (
            profile_name TEXT PRIMARY KEY,
            mapping_json TEXT,
            created_date TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS output_column_mappings (
            profile_name TEXT PRIMARY KEY,
            mapping_json TEXT,
            created_date TEXT
        )""")

        # Migration: Add client_code column if it doesn't exist
        try:
            c.execute("PRAGMA table_info(parts_master)")
            columns = [col[1] for col in c.fetchall()]
            if 'client_code' not in columns:
                c.execute("ALTER TABLE parts_master ADD COLUMN client_code TEXT")
        except:
            pass
        
        conn.commit()
        conn.close()


class PostgreSQLBackend(DatabaseBackend):
    """PostgreSQL database backend for multi-user sync operation"""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 is not installed. Run: pip install psycopg2-binary")
        
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
    
    def connect(self):
        return psycopg2.connect(**self.connection_params)
    
    def get_placeholder(self):
        return "%s"
    
    def init_schema(self):
        conn = self.connect()
        c = conn.cursor()
        
        c.execute("""CREATE TABLE IF NOT EXISTS parts_master (
            part_number TEXT PRIMARY KEY,
            description TEXT,
            hts_code TEXT,
            country_origin TEXT,
            mid TEXT,
            client_code TEXT,
            steel_ratio REAL DEFAULT 1.0,
            non_steel_ratio REAL DEFAULT 0.0,
            last_updated TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS tariff_232 (
            hts_code TEXT PRIMARY KEY,
            material TEXT,
            classification TEXT,
            chapter TEXT,
            chapter_description TEXT,
            declaration_required TEXT,
            notes TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS sec_232_actions (
            tariff_no TEXT PRIMARY KEY,
            action TEXT,
            description TEXT,
            advalorem_rate TEXT,
            effective_date TEXT,
            expiration_date TEXT,
            specific_rate TEXT,
            additional_declaration TEXT,
            note TEXT,
            link TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS mapping_profiles (
            profile_name TEXT PRIMARY KEY,
            mapping_json TEXT,
            created_date TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS output_column_mappings (
            profile_name TEXT PRIMARY KEY,
            mapping_json TEXT,
            created_date TEXT
        )""")

        conn.commit()
        conn.close()


class DatabaseManager:
    """
    Central database manager that handles connection pooling and provides
    a unified interface for both SQLite and PostgreSQL backends.
    """
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path(__file__).parent / "db_config.json"
        self.backend = None
        self._load_config()
    
    def _load_config(self):
        """Load database configuration from file or use SQLite default"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        else:
            # Default to SQLite
            config = {
                'type': 'sqlite',
                'sqlite': {
                    'path': str(Path(__file__).parent / "Resources" / "derivativemill.db")
                }
            }
            self._save_config(config)
        
        self._init_backend(config)
    
    def _save_config(self, config: dict):
        """Save database configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _init_backend(self, config: dict):
        """Initialize the appropriate database backend"""
        db_type = config.get('type', 'sqlite')
        
        if db_type == 'sqlite':
            sqlite_config = config.get('sqlite', {})
            db_path = Path(sqlite_config.get('path', 'derivativemill.db'))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.backend = SQLiteBackend(db_path)
        
        elif db_type == 'postgresql':
            pg_config = config.get('postgresql', {})
            self.backend = PostgreSQLBackend(
                host=pg_config.get('host', 'localhost'),
                port=pg_config.get('port', 5432),
                database=pg_config.get('database', 'derivativemill'),
                user=pg_config.get('user', 'postgres'),
                password=pg_config.get('password', '')
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def configure_postgresql(self, host: str, port: int, database: str, user: str, password: str):
        """Configure the application to use PostgreSQL"""
        config = {
            'type': 'postgresql',
            'postgresql': {
                'host': host,
                'port': port,
                'database': database,
                'user': user,
                'password': password
            }
        }
        self._save_config(config)
        self._init_backend(config)
        self.init_database()
    
    def configure_sqlite(self, db_path: str = None):
        """Configure the application to use SQLite"""
        if db_path is None:
            db_path = str(Path(__file__).parent / "Resources" / "derivativemill.db")
        
        config = {
            'type': 'sqlite',
            'sqlite': {
                'path': db_path
            }
        }
        self._save_config(config)
        self._init_backend(config)
        self.init_database()
    
    def get_config(self) -> dict:
        """Get current database configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {'type': 'sqlite'}
    
    def is_postgresql(self) -> bool:
        """Check if currently using PostgreSQL"""
        return isinstance(self.backend, PostgreSQLBackend)
    
    def is_sqlite(self) -> bool:
        """Check if currently using SQLite"""
        return isinstance(self.backend, SQLiteBackend)
    
    @contextmanager
    def connection(self):
        """Context manager for database connections"""
        conn = self.backend.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def connect(self):
        """Get a database connection (caller must close)"""
        return self.backend.connect()
    
    def get_placeholder(self) -> str:
        """Get the SQL parameter placeholder for the current backend"""
        return self.backend.get_placeholder()
    
    def init_database(self):
        """Initialize the database schema"""
        self.backend.init_schema()
    
    def execute(self, query: str, params: tuple = None):
        """Execute a query and return the cursor"""
        conn = self.connect()
        c = conn.cursor()
        if params:
            c.execute(query, params)
        else:
            c.execute(query)
        conn.commit()
        result = c.fetchall() if c.description else None
        conn.close()
        return result
    
    def execute_many(self, query: str, params_list: list):
        """Execute a query with multiple parameter sets"""
        conn = self.connect()
        c = conn.cursor()
        c.executemany(query, params_list)
        conn.commit()
        conn.close()


def migrate_sqlite_to_postgresql(sqlite_path: Path, pg_manager: DatabaseManager):
    """
    Migrate data from SQLite database to PostgreSQL.
    
    Args:
        sqlite_path: Path to the SQLite database file
        pg_manager: DatabaseManager configured for PostgreSQL
    """
    if not pg_manager.is_postgresql():
        raise ValueError("Target database manager must be configured for PostgreSQL")
    
    import pandas as pd
    
    # Connect to SQLite source
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    
    # Tables to migrate
    tables = ['parts_master', 'tariff_232', 'sec_232_actions', 'mapping_profiles', 'app_config']
    
    for table in tables:
        try:
            # Read from SQLite
            df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
            
            if df.empty:
                print(f"  {table}: No data to migrate")
                continue
            
            # Write to PostgreSQL
            pg_conn = pg_manager.connect()
            
            # Build INSERT statement
            columns = ', '.join(df.columns)
            placeholders = ', '.join(['%s'] * len(df.columns))
            
            insert_sql = f"""
                INSERT INTO {table} ({columns}) 
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            c = pg_conn.cursor()
            for _, row in df.iterrows():
                c.execute(insert_sql, tuple(row))
            
            pg_conn.commit()
            pg_conn.close()
            
            print(f"  {table}: Migrated {len(df)} rows")
            
        except Exception as e:
            print(f"  {table}: Error - {e}")
    
    sqlite_conn.close()
    print("\nMigration complete!")


# Global database manager instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def init_db_manager(config_path: Path = None) -> DatabaseManager:
    """Initialize and return the global database manager"""
    global _db_manager
    _db_manager = DatabaseManager(config_path)
    return _db_manager
