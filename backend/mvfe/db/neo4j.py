"""
Neo4j connection management (optional).
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_neo4j_driver():
    """
    Create Neo4j driver if configured, otherwise return None.
    Requires NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars.
    """
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        logger.info("[neo4j] Not configured (NEO4J_URI/NEO4J_PASSWORD not set), disabled")
        return None

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        logger.info(f"[neo4j] Connected to {uri}")
        return driver
    except ImportError:
        logger.warning("[neo4j] neo4j package not installed, disabled")
        return None
    except Exception as e:
        logger.warning(f"[neo4j] Connection failed: {e}, disabled")
        return None
