from sqlmodel import SQLModel, create_engine, Session

# Database configuration
DATABASE_URL = "postgresql://localhost:5432/babyfoot"  # Replace with your credentials

# Create the database engine
engine = create_engine(DATABASE_URL, echo=True)


# Initialize the database schema (create tables if they don't exist)
def init_db():
    SQLModel.metadata.create_all(engine)


# Dependency for getting a database session

def get_session():
    with Session(engine) as session:
        yield session
