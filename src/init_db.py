from src.database import engine, Base
from src.models import Node

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database initialized.")