from app.core.database import get_session

with get_session() as session:
    result = session.run("RETURN 'Neo4j connected!' AS message")
    print(result.single()["message"])