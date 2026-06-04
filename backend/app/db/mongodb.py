"""
MongoDB Atlas connection utility — Motor async driver.

Secret resolution order for MONGODB_URI:
  1. AWS Secrets Manager  (secret name: "ai-camera/mongodb-uri")
     → Used in production — credentials never stored in files
  2. Environment variable  MONGODB_URI  (from .env)
     → Used in local development

Responsibilities:
  1.  Resolve MONGODB_URI securely (Secrets Manager → .env fallback)
  2.  Connect to the 'ai_camera_platform' database
  3.  Verify connectivity with an admin ping
  4.  Ensure the analytics_snapshots time-series collection exists
  5.  Create all blueprint indexes on startup (idempotent)
  6.  Seed the default ModelConfig document if none exists
  7.  Expose get_db() / get_client() for service layer access

Startup logs:
  ====================================
  🚀 Backend Starting...
  ====================================

  🔐 Secret source: AWS Secrets Manager   ← production
       OR
  🔐 Secret source: .env file             ← local dev

  ✅ MongoDB Connected
  📂 Database: ai_camera_platform
  📡 Atlas Ping Successful
  🗂  Collections verified
  📌 Indexes ensured

  ====================================
  ✅ Server Ready
  ====================================
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import (
    CollectionInvalid,
    ConfigurationError,
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from app.core.config import DB_NAME

# ── Load .env (local dev fallback) ────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")
load_dotenv(dotenv_path=_ENV_PATH)


# ── AWS Secrets Manager helper ─────────────────────────────────────────────────

def _get_secret_from_aws(secret_name: str) -> str | None:
    """
    Fetch a secret string from AWS Secrets Manager.
    Returns None if:
      - boto3 is not installed
      - AWS credentials are not configured
      - The secret does not exist
    This ensures local dev always works without AWS setup.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        client = boto3.client("secretsmanager", region_name="us-east-1")
        response = client.get_secret_value(SecretId=secret_name)

        # Secret can be a plain string or a JSON object
        secret = response.get("SecretString", "")
        try:
            return json.loads(secret).get("MONGODB_URI", secret)
        except (json.JSONDecodeError, AttributeError):
            return secret  # plain string — return as-is

    except ImportError:
        return None   # boto3 not installed — use .env
    except Exception:  # noqa: BLE001 — NoCredentialsError, ClientError, etc.
        return None   # AWS not reachable — use .env


def _resolve_mongodb_uri() -> str | None:
    """
    Resolve MONGODB_URI using the secure priority order:
      1. AWS Secrets Manager  → production / deployed environments
      2. MONGODB_URI env var  → local development (.env file)
    """
    # 1️⃣ Try AWS Secrets Manager first
    uri = _get_secret_from_aws("ai-camera/mongodb-uri")
    if uri:
        print("🔐 Secret source: AWS Secrets Manager")
        return uri

    # 2️⃣ Fallback to environment variable (loaded from .env above)
    uri = os.getenv("MONGODB_URI")
    if uri:
        print("🔐 Secret source: .env file (local dev)")
        return uri

    return None

# ── Module-level singletons ────────────────────────────────────────────────────
_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
_db: motor.motor_asyncio.AsyncIOMotorDatabase | None = None


# ── Public accessors ───────────────────────────────────────────────────────────

def get_client() -> motor.motor_asyncio.AsyncIOMotorClient | None:
    """Return the active Motor client (None if not connected)."""
    return _client


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase | None:
    """Return the 'ai_camera_platform' database handle (None if not connected)."""
    return _db


# ── Connect ────────────────────────────────────────────────────────────────────

async def connect_to_mongodb() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Establish a connection to MongoDB Atlas and initialise the database.

    Idempotent — safe to call multiple times (hot-reload guard via _client check).
    Calls sys.exit(1) on any connection failure.
    """
    global _client, _db

    if _client is not None:          # already connected — skip
        return _client

    uri = _resolve_mongodb_uri()
    if not uri:
        _print_failure_banner(
            "MONGODB_URI could not be resolved.\n"
            "  • Production: ensure AWS Secrets Manager secret 'ai-camera/mongodb-uri' exists.\n"
            "  • Local dev:  ensure MONGODB_URI is set in backend/.env"
        )
        sys.exit(1)

    print("\n====================================")
    print("🚀 Backend Starting...")
    print("====================================\n")

    try:
        _client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5_000,
        )

        # Force a real round-trip to validate the connection
        await _client.admin.command("ping")

        # Always use the canonical DB name from config
        _db = _client[DB_NAME]

        print("✅ MongoDB Connected")
        print(f"📂 Database: {DB_NAME}")

        # Second ping for confirmation
        await _client.admin.command("ping")
        print("📡 Atlas Ping Successful")

        # Prepare collections and indexes
        await _ensure_collections()
        await _ensure_indexes()
        await _seed_default_model_config()

        print("\n====================================")
        print("✅ Server Ready")
        print("====================================\n")

        return _client

    except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as exc:
        _print_failure_banner(str(exc))
        sys.exit(1)
    except Exception as exc:          # noqa: BLE001
        _print_failure_banner(f"Unexpected error: {exc}")
        sys.exit(1)


# ── Disconnect ─────────────────────────────────────────────────────────────────

async def disconnect_from_mongodb() -> None:
    """Gracefully close the Motor client. Safe to call when not connected."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


# ── Collection bootstrap ───────────────────────────────────────────────────────

async def _ensure_collections() -> None:
    """
    Create any collections that require special options (time-series).
    Standard collections are created implicitly by MongoDB on first write.
    """
    existing = set(await _db.list_collection_names())

    # ── analytics_snapshots — native time-series collection ───────────────────
    if "analytics_snapshots" not in existing:
        try:
            await _db.create_collection(
                "analytics_snapshots",
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "meta",
                    "granularity": "seconds",
                },
            )
            print("   🕒 analytics_snapshots time-series collection created")
        except (CollectionInvalid, OperationFailure):
            pass  # another process beat us to it — that's fine

    print("🗂  Collections verified")


# ── Index creation ─────────────────────────────────────────────────────────────

async def _ensure_indexes() -> None:
    """
    Create all indexes defined in the database architecture blueprint.
    Motor's create_index / create_indexes calls are idempotent —
    existing identical indexes are silently ignored.
    """

    # ── users ─────────────────────────────────────────────────────────────────
    users = _db["users"]
    await users.create_index([("email", ASCENDING)], unique=True, name="users_email_unique")
    await users.create_index([("org_id", ASCENDING), ("role", ASCENDING)], name="users_org_role")
    await users.create_index([("is_active", ASCENDING)], name="users_is_active")

    # ── cameras ───────────────────────────────────────────────────────────────
    cameras = _db["cameras"]
    await cameras.create_index(
        [("org_id", ASCENDING), ("status", ASCENDING)], name="cameras_org_status"
    )
    await cameras.create_index(
        [("org_id", ASCENDING), ("location.zone", ASCENDING)], name="cameras_org_zone"
    )
    await cameras.create_index([("tags", ASCENDING)], name="cameras_tags")
    await cameras.create_index(
        [("last_active_at", DESCENDING)], name="cameras_last_active"
    )

    # ── video_uploads ─────────────────────────────────────────────────────────
    uploads = _db["video_uploads"]
    await uploads.create_index(
        [("org_id", ASCENDING), ("uploaded_at", DESCENDING)], name="uploads_org_date"
    )
    await uploads.create_index(
        [("uploaded_by", ASCENDING), ("uploaded_at", DESCENDING)], name="uploads_user_date"
    )
    await uploads.create_index(
        [("expires_at", ASCENDING)],
        name="uploads_ttl",
        sparse=True,
        expireAfterSeconds=0,   # document's own expires_at controls the exact time
    )
    await uploads.create_index(
        [("status", ASCENDING), ("uploaded_at", DESCENDING)], name="uploads_status_date"
    )
    # Secondary lookup: stored_filename is used as the backward-compat video_id
    await uploads.create_index(
        [("stored_filename", ASCENDING)], name="uploads_stored_filename"
    )

    # ── sessions ──────────────────────────────────────────────────────────────
    sessions = _db["sessions"]
    await sessions.create_index(
        [("org_id", ASCENDING), ("status", ASCENDING), ("started_at", DESCENDING)],
        name="sessions_org_status_date",
    )
    await sessions.create_index(
        [("camera_id", ASCENDING), ("started_at", DESCENDING)], name="sessions_camera_date"
    )
    await sessions.create_index(
        [("created_by", ASCENDING), ("started_at", DESCENDING)], name="sessions_user_date"
    )
    await sessions.create_index(
        [("summary.peak_person_count", DESCENDING)], name="sessions_peak_count"
    )
    await sessions.create_index(
        [("status", ASCENDING), ("started_at", ASCENDING)], name="sessions_queue"
    )

    # ── analytics_snapshots (time-series — extra compound indexes) ────────────
    snapshots = _db["analytics_snapshots"]
    await snapshots.create_index(
        [("meta.session_id", ASCENDING), ("timestamp", ASCENDING)],
        name="snapshots_session_time",
    )
    await snapshots.create_index(
        [("meta.camera_id", ASCENDING), ("timestamp", DESCENDING)],
        name="snapshots_camera_time",
    )

    # ── alerts ────────────────────────────────────────────────────────────────
    alerts = _db["alerts"]
    await alerts.create_index(
        [("org_id", ASCENDING), ("triggered_at", DESCENDING)], name="alerts_org_date"
    )
    await alerts.create_index(
        [("camera_id", ASCENDING), ("severity", ASCENDING), ("triggered_at", DESCENDING)],
        name="alerts_camera_severity_date",
    )
    await alerts.create_index(
        [("is_acknowledged", ASCENDING), ("triggered_at", DESCENDING)],
        name="alerts_ack_queue",
    )
    await alerts.create_index(
        [("session_id", ASCENDING), ("type", ASCENDING)], name="alerts_session_type"
    )

    # ── model_configs ─────────────────────────────────────────────────────────
    configs = _db["model_configs"]
    await configs.create_index([("is_default", ASCENDING)], name="configs_default")
    await configs.create_index(
        [("org_id", ASCENDING), ("name", ASCENDING)], name="configs_org_name"
    )

    # ── incidents ─────────────────────────────────────────────────────────────
    incidents = _db["incidents"]
    await incidents.create_index(
        [("org_id", ASCENDING), ("status", ASCENDING), ("occurred_at", DESCENDING)],
        name="incidents_org_status_date",
    )
    await incidents.create_index(
        [("org_id", ASCENDING), ("category", ASCENDING), ("severity", ASCENDING)],
        name="incidents_org_category_severity",
    )
    await incidents.create_index(
        [("created_by", ASCENDING), ("occurred_at", DESCENDING)],
        name="incidents_creator_date",
    )

    print("📌 Indexes ensured")


# ── Seed default model config ──────────────────────────────────────────────────

async def _seed_default_model_config() -> None:
    """
    Insert the system default ModelConfig document on first startup.
    Idempotent — does nothing if a default config already exists.
    """
    from app.models.model_config import DEFAULT_MODEL_CONFIG

    configs = _db["model_configs"]
    existing = await configs.find_one({"is_default": True})
    if existing is None:
        doc = {**DEFAULT_MODEL_CONFIG, "created_at": datetime.utcnow()}
        await configs.insert_one(doc)
        print("   🌱 Default ModelConfig seeded")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _print_failure_banner(detail: str) -> None:
    print("\n====================================")
    print("❌ MongoDB Connection Failed")
    print(detail)
    print("====================================\n")
