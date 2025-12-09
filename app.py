"""
AutoGSC Web Dashboard
A simple Flask web interface for the AutoGSC tool.
"""
from flask import Flask, render_template, jsonify, request
from threading import Thread
import subprocess
import os
import sys

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_stats, get_today_submission_count, get_connection
from config import SITE_URL, SITEMAP_URL, DAILY_SUBMISSION_LIMIT

app = Flask(__name__)

# Track running jobs
current_job = {"running": False, "status": "", "log": []}


def run_autogsc_job():
    """Run the AutoGSC scan and submit in background."""
    global current_job
    current_job["running"] = True
    current_job["log"] = []
    current_job["status"] = "Starting..."
    
    try:
        # Run the main.py script
        process = subprocess.Popen(
            [sys.executable, "main.py", "run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        current_job["status"] = "Scanning sitemap..."
        
        for line in process.stdout:
            line = line.strip()
            if line:
                current_job["log"].append(line)
                # Update status based on output
                if "Scanning" in line:
                    current_job["status"] = "Scanning sitemap..."
                elif "Submitting" in line:
                    current_job["status"] = "Submitting URLs..."
                elif "Complete" in line:
                    current_job["status"] = "Complete!"
        
        process.wait()
        current_job["status"] = "Complete!"
        
    except Exception as e:
        current_job["status"] = f"Error: {str(e)}"
        current_job["log"].append(f"Error: {str(e)}")
    finally:
        current_job["running"] = False


def get_recent_submissions(limit=10):
    """Get recent submission history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT url, submitted_at, result 
        FROM submissions 
        ORDER BY submitted_at DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"url": r[0], "time": r[1], "result": r[2]} for r in rows]


def get_url_breakdown():
    """Get breakdown of URLs by status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT indexing_status, COUNT(*) 
        FROM urls 
        GROUP BY indexing_status
    """)
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("dashboard.html")


@app.route("/api/stats")
def api_stats():
    """Get current statistics."""
    stats = get_stats()
    stats["today_limit"] = DAILY_SUBMISSION_LIMIT
    stats["site_url"] = SITE_URL
    stats["sitemap_url"] = SITEMAP_URL
    stats["breakdown"] = get_url_breakdown()
    return jsonify(stats)


@app.route("/api/history")
def api_history():
    """Get recent submission history."""
    return jsonify(get_recent_submissions(20))


@app.route("/api/job/status")
def api_job_status():
    """Get current job status."""
    return jsonify(current_job)


@app.route("/api/job/start", methods=["POST"])
def api_job_start():
    """Start a new scan/submit job."""
    if current_job["running"]:
        return jsonify({"error": "Job already running"}), 400
    
    thread = Thread(target=run_autogsc_job)
    thread.start()
    return jsonify({"status": "started"})


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  AutoGSC Dashboard")
    print("  Open: http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)
