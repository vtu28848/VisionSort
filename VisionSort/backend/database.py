import os
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VisionSortDB")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "visionsort_db"

class VisionSortDatabase:
    """
    Manages data persistence for VisionSort.
    Tries to connect to MongoDB, falling back to a local SQLite database
    if MongoDB is unavailable, ensuring out-of-the-box functionality.
    """
    def __init__(self):
        self.is_fallback = False
        self.mongo_client = None
        self.mongo_db = None
        self.sqlite_path = os.path.join(os.path.dirname(__file__) or ".", "visionsort_fallback.db")
        
    async def initialize(self):
        try:
            logger.info(f"Connecting to MongoDB at {MONGO_URI}...")
            # Set a 2-second timeout so the fallback triggers quickly
            self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGO_URI, 
                serverSelectionTimeoutMS=2000
            )
            # Force connection ping
            await self.mongo_client.admin.command('ping')
            self.mongo_db = self.mongo_client[DB_NAME]
            self.is_fallback = False
            logger.info("Successfully connected to MongoDB!")
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            logger.warning(f"MongoDB connection failed: {e}. Falling back to SQLite database at {self.sqlite_path}")
            self.is_fallback = True
            self.init_sqlite()
            
    def init_sqlite(self):
        """Initializes SQLite schema if fallback is activated."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        # Create sorting events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sorting_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                category TEXT,
                confidence REAL,
                status TEXT,
                conveyor_speed REAL
            )
        """)
        
        # Create hourly trends table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_metrics (
                hour_start TEXT PRIMARY KEY,
                total_items INTEGER,
                plastic_count INTEGER,
                metal_count INTEGER,
                biological_count INTEGER,
                paper_count INTEGER,
                contamination_faults INTEGER
            )
        """)
        conn.commit()
        
        # Pre-populate with 12 hours of mock data if empty
        cursor.execute("SELECT COUNT(*) FROM hourly_metrics")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("Pre-populating SQLite fallback database with 12 hours of mock historical data...")
            now = datetime.now()
            for i in range(12, 0, -1):
                time_slot = now - timedelta(hours=i)
                hour_str = time_slot.strftime("%Y-%m-%dT%H:00:00")
                
                t = random.randint(150, 300)
                p = int(t * random.uniform(0.3, 0.4))
                m = int(t * random.uniform(0.25, 0.35))
                b = int(t * random.uniform(0.15, 0.25))
                pa = t - p - m - b
                f = int(t * random.uniform(0.01, 0.05))
                
                cursor.execute(
                    """
                    INSERT INTO hourly_metrics (hour_start, total_items, plastic_count, metal_count, biological_count, paper_count, contamination_faults)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (hour_str, t, p, m, b, pa, f)
                )
            conn.commit()
            
        conn.close()
        logger.info("SQLite fallback tables initialized.")

    async def log_sorting_event(self, category: str, confidence: float, status: str, conveyor_speed: float):
        """Logs a single sorting classification event."""
        now = datetime.now()
        timestamp_str = now.isoformat()
        
        if not self.is_fallback:
            try:
                event = {
                    "timestamp": now,
                    "category": category,
                    "confidence": confidence,
                    "status": status,
                    "conveyor_speed": conveyor_speed
                }
                await self.mongo_db.sorting_events.insert_one(event)
                await self._update_mongo_hourly_metrics(category, status, now)
                return
            except Exception as e:
                logger.error(f"Failed to log to MongoDB: {e}. Falling back to SQLite...")
                self.is_fallback = True
                self.init_sqlite()
                
        # SQLite execution (blocking, run in executor)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._log_sqlite_event, timestamp_str, category, confidence, status, conveyor_speed)

    def _log_sqlite_event(self, timestamp: str, category: str, confidence: float, status: str, conveyor_speed: float):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        # Insert event
        cursor.execute(
            "INSERT INTO sorting_events (timestamp, category, confidence, status, conveyor_speed) VALUES (?, ?, ?, ?, ?)",
            (timestamp, category, confidence, status, conveyor_speed)
        )
        
        # Update hourly metrics
        hour_start = timestamp[:13] + ":00:00"  # Format: YYYY-MM-DDTHH:00:00
        
        is_plastic = 1 if category == "Plastic" else 0
        is_metal = 1 if category == "Metal" else 0
        is_bio = 1 if category == "Biological" else 0
        is_paper = 1 if category == "Paper" else 0
        is_fault = 1 if status == "Fault" else 0
        
        cursor.execute(
            """
            INSERT INTO hourly_metrics (hour_start, total_items, plastic_count, metal_count, biological_count, paper_count, contamination_faults)
            VALUES (?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(hour_start) DO UPDATE SET
                total_items = total_items + 1,
                plastic_count = plastic_count + ?,
                metal_count = metal_count + ?,
                biological_count = biological_count + ?,
                paper_count = paper_count + ?,
                contamination_faults = contamination_faults + ?
            """,
            (hour_start, is_plastic, is_metal, is_bio, is_paper, is_fault, is_plastic, is_metal, is_bio, is_paper, is_fault)
        )
        conn.commit()
        conn.close()

    async def _update_mongo_hourly_metrics(self, category: str, status: str, now: datetime):
        """Helper to increment fields in MongoDB hourly rollup."""
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        is_plastic = 1 if category == "Plastic" else 0
        is_metal = 1 if category == "Metal" else 0
        is_bio = 1 if category == "Biological" else 0
        is_paper = 1 if category == "Paper" else 0
        is_fault = 1 if status == "Fault" else 0
        
        await self.mongo_db.hourly_metrics.update_one(
            {"hour_start": hour_start},
            {
                "$inc": {
                    "total_items": 1,
                    "plastic_count": is_plastic,
                    "metal_count": is_metal,
                    "biological_count": is_bio,
                    "paper_count": is_paper,
                    "contamination_faults": is_fault
                }
            },
            upsert=True
        )

    async def get_hourly_trends(self, limit: int = 12):
        """Retrieves hourly throughput and sorting metrics for the charts."""
        if not self.is_fallback:
            try:
                cursor = self.mongo_db.hourly_metrics.find().sort("hour_start", -1).limit(limit)
                mongo_trends = await cursor.to_list(length=limit)
                
                # Format for frontend chart
                trends = []
                for entry in reversed(mongo_trends):
                    dt = entry["hour_start"]
                    # If it's a string, parse it. In Mongo it's a datetime object.
                    hour_label = dt.strftime("%H:%M") if isinstance(dt, datetime) else str(dt)[:16]
                    trends.append({
                        "hour": hour_label,
                        "total": entry.get("total_items", 0),
                        "plastics": entry.get("plastic_count", 0),
                        "metals": entry.get("metal_count", 0),
                        "biological": entry.get("biological_count", 0),
                        "paper": entry.get("paper_count", 0),
                        "faults": entry.get("contamination_faults", 0)
                    })
                
                if trends:
                    return trends
            except Exception as e:
                logger.error(f"Failed to fetch hourly trends from MongoDB: {e}")
                
        # SQLite fallback retrieval
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_sqlite_trends, limit)

    def _get_sqlite_trends(self, limit: int):
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT hour_start, total_items, plastic_count, metal_count, biological_count, paper_count, contamination_faults "
            "FROM hourly_metrics ORDER BY hour_start DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        trends = []
        for row in reversed(rows):
            # Parse SQLite hour start string
            dt_str = row[0]
            try:
                dt = datetime.fromisoformat(dt_str)
                hour_label = dt.strftime("%H:%M")
            except:
                hour_label = dt_str[11:16]
                
            trends.append({
                "hour": hour_label,
                "total": row[1],
                "plastics": row[2],
                "metals": row[3],
                "biological": row[4],
                "paper": row[5],
                "faults": row[6]
            })
            
        # If no data exists, generate some mock historical data to populate charts immediately
        if not trends:
            trends = self._generate_mock_trends()
            
        return trends

    def _generate_mock_trends(self):
        """Generates mock historical data if database is fresh/empty."""
        trends = []
        now = datetime.now()
        for i in range(12, 0, -1):
            time_slot = now - timedelta(hours=i)
            # Create some nice distribution
            t = random.randint(150, 300)
            p = int(t * random.uniform(0.3, 0.4))
            m = int(t * random.uniform(0.25, 0.35))
            b = int(t * random.uniform(0.15, 0.25))
            pa = t - p - m - b
            f = int(t * random.uniform(0.01, 0.05))
            trends.append({
                "hour": time_slot.strftime("%H:%M"),
                "total": t,
                "plastics": p,
                "metals": m,
                "biological": b,
                "paper": pa,
                "faults": f
            })
        return trends

    def get_status_label(self) -> str:
        return "SQLite Fallback Mode" if self.is_fallback else "MongoDB Connected"

# Global database instance
db = VisionSortDatabase()
import random
