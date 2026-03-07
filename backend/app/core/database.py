from neo4j import GraphDatabase
from app.core.config import settings

driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
)

def get_session():
    return driver.session()