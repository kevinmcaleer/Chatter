from sqlmodel import SQLModel, Session, create_engine

sqlite_file_name = "database.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}", echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
