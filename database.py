"""
Database Module
SQLite storage for tracking URLs and submission history.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from config import DATABASE_PATH, RESUBMIT_AFTER_HOURS


def get_connection():
    """Get database connection."""
    return sqlite3.connect(DATABASE_PATH)


def init_database():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # URLs table - tracks all known URLs and their status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            url TEXT PRIMARY KEY,
            indexing_status TEXT,
            last_checked TIMESTAMP,
            last_submitted TIMESTAMP,
            submission_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Submissions table - log of all submission attempts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT,
            error_message TEXT,
            FOREIGN KEY (url) REFERENCES urls(url)
        )
    """)
    
    # Daily quota tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_quota (
            date TEXT PRIMARY KEY,
            submissions_count INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()


def upsert_url(url: str, indexing_status: str):
    """Insert or update a URL's indexing status."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO urls (url, indexing_status, last_checked)
        VALUES (?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            indexing_status = excluded.indexing_status,
            last_checked = excluded.last_checked
    """, (url, indexing_status, datetime.now()))
    
    conn.commit()
    conn.close()


def get_unindexed_urls() -> List[str]:
    """Get all URLs that are not indexed and haven't been submitted recently."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(hours=RESUBMIT_AFTER_HOURS)
    
    cursor.execute("""
        SELECT url FROM urls
        WHERE indexing_status IN ('Discovered - currently not indexed', 
                                   'Crawled - currently not indexed',
                                   'not_indexed')
        AND (last_submitted IS NULL OR last_submitted < ?)
        ORDER BY last_checked ASC
    """, (cutoff_time,))
    
    urls = [row[0] for row in cursor.fetchall()]
    conn.close()
    return urls


def record_submission(url: str, result: str, error_message: Optional[str] = None):
    """Record a submission attempt."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Log the submission
    cursor.execute("""
        INSERT INTO submissions (url, result, error_message)
        VALUES (?, ?, ?)
    """, (url, result, error_message))
    
    # Update the URL record
    cursor.execute("""
        UPDATE urls 
        SET last_submitted = ?, submission_count = submission_count + 1
        WHERE url = ?
    """, (datetime.now(), url))
    
    # Update daily quota
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO daily_quota (date, submissions_count)
        VALUES (?, 1)
        ON CONFLICT(date) DO UPDATE SET
            submissions_count = submissions_count + 1
    """, (today,))
    
    conn.commit()
    conn.close()


def get_today_submission_count() -> int:
    """Get number of submissions made today."""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT submissions_count FROM daily_quota WHERE date = ?", (today,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else 0


def get_stats() -> Dict[str, Any]:
    """Get overall statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total URLs
    cursor.execute("SELECT COUNT(*) FROM urls")
    stats["total_urls"] = cursor.fetchone()[0]
    
    # Indexed URLs
    cursor.execute("SELECT COUNT(*) FROM urls WHERE indexing_status = 'indexed'")
    stats["indexed"] = cursor.fetchone()[0]
    
    # Pending - submitted recently but still not indexed
    cutoff_time = datetime.now() - timedelta(hours=RESUBMIT_AFTER_HOURS)
    cursor.execute("""
        SELECT COUNT(*) FROM urls 
        WHERE indexing_status IN ('Discovered - currently not indexed', 
                                   'Crawled - currently not indexed',
                                   'not_indexed')
        AND last_submitted IS NOT NULL 
        AND last_submitted >= ?
    """, (cutoff_time,))
    stats["pending"] = cursor.fetchone()[0]
    
    # Unindexed URLs (not yet submitted or submission expired)
    cursor.execute("""
        SELECT COUNT(*) FROM urls 
        WHERE indexing_status IN ('Discovered - currently not indexed', 
                                   'Crawled - currently not indexed',
                                   'not_indexed')
        AND (last_submitted IS NULL OR last_submitted < ?)
    """, (cutoff_time,))
    stats["unindexed"] = cursor.fetchone()[0]
    
    # Today's submissions
    stats["today_submissions"] = get_today_submission_count()
    
    # Total submissions all time
    cursor.execute("SELECT COUNT(*) FROM submissions")
    stats["total_submissions"] = cursor.fetchone()[0]
    
    conn.close()
    return stats


# Initialize database on import
init_database()
