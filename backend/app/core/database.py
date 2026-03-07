"""Neo4j driver initialisation and session management.

- Reads credentials from ``app.core.config.settings`` (sourced from ``.env``)
- Enables connection-pooling via the driver's built-in pool
- Exposes ``get_session()`` for use across all modules
- Provides ``verify_connectivity()`` for health-check / startup probes
"""

import logging

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Driver (singleton – reused across the entire application)
# ---------------------------------------------------------------------------
# The Neo4j Python driver manages an internal connection pool automatically.
# ``max_connection_pool_size`` caps the pool; ``connection_acquisition_timeout``
# limits how long a caller waits for a free connection.
# ---------------------------------------------------------------------------
try:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_pool_size=50,
        connection_acquisition_timeout=30,
    )
    logger.info("Neo4j driver created for %s", settings.neo4j_uri)
except Exception as exc:
    logger.error("Failed to create Neo4j driver: %s", exc)
    driver = None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_session():
    """Return a new Neo4j session (must be used as a context-manager).

    Raises ``RuntimeError`` if the driver could not be initialised.
    """
    if driver is None:
        raise RuntimeError(
            "Neo4j driver is not initialised. "
            "Check NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD in your .env file."
        )
    return driver.session()


def verify_connectivity():
    """Ping the Neo4j server and return True / False.

    Useful for startup checks and health-check endpoints.
    """
    if driver is None:
        return False
    try:
        driver.verify_connectivity()
        logger.info("Neo4j connectivity verified successfully.")
        return True
    except (ServiceUnavailable, AuthError) as exc:
        logger.error("Neo4j connectivity check failed: %s", exc)
        return False