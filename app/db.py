from sqlmodel import Session, create_engine

DATABASE_FILE = "verity_db.sqlite3"
DATABASE_URI = f"sqlite:///data/{DATABASE_FILE}"

engine = create_engine(DATABASE_URI)


def get_session():
    return Session(engine)
