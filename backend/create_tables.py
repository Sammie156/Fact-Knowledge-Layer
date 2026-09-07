from core.database import Base, engine
from core import models

Base.metadata.create_all(engine)