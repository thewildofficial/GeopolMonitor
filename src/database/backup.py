"""Database backup utilities."""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

def backup_database(db_path: str, backup_dir: str = "backups") -> None:
    """Create a backup of the database file.
    
    Args:
        db_path: Path to the SQLite database file
        backup_dir: Directory to store backups (relative to db_path)
    """
    db_path = Path(db_path)
    if not db_path.exists():
        logger.warning(f"Database file {db_path} not found")
        return
        
    # Create backup directory if it doesn't exist
    backup_path = db_path.parent / backup_dir
    backup_path.mkdir(exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"news_monitor_{timestamp}.db"
    
    # Copy database file
    try:
        # First create a connection and backup using SQLite's backup API
        with sqlite3.connect(str(db_path)) as src, \
             sqlite3.connect(str(backup_file)) as dst:
            src.backup(dst)
        
        logger.info(f"Database backed up to {backup_file}")
        
        # Clean up old backups (keep last 5)
        existing_backups = sorted(backup_path.glob("news_monitor_*.db"))
        if len(existing_backups) > 5:
            for old_backup in existing_backups[:-5]:
                old_backup.unlink()
                logger.info(f"Removed old backup {old_backup}")
                
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        if backup_file.exists():
            backup_file.unlink()  # Clean up failed backup

def restore_database(backup_file: str, db_path: str) -> bool:
    """Restore database from a backup file.
    
    Args:
        backup_file: Path to the backup file
        db_path: Path to restore the database to
        
    Returns:
        bool: True if restore was successful
    """
    backup_path = Path(backup_file)
    db_path = Path(db_path)
    
    if not backup_path.exists():
        logger.error(f"Backup file {backup_path} not found")
        return False
        
    try:
        # Create a new connection and restore using SQLite's backup API
        with sqlite3.connect(str(backup_path)) as src, \
             sqlite3.connect(str(db_path)) as dst:
            src.backup(dst)
            
        logger.info(f"Database restored from {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False