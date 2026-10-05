from database import Base, engine
from models import User, Message, UserContext

Base.metadata.create_all(engine)

print("Tables created successfully!")