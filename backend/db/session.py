from sqlmodel import SQLModel, create_engine, Session

from ..settings import settings

# Create the database engine
engine = create_engine(settings.DATABASE_URL, echo=False)


# Initialize the database schema (create tables if they don't exist)
def init_db():
    SQLModel.metadata.create_all(engine)


# Dependency for getting a database session

def get_session():
    with Session(engine) as session:
        yield session
