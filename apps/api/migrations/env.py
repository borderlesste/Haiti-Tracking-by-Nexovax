from alembic import context
from app.core import Settings, database
from app.models import Base

config = context.config
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=Settings().database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine, _ = database(Settings())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
