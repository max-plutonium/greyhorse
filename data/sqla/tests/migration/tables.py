from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column as C


class Base(DeclarativeBase):
    pass


metadata = Base.metadata
metadata.schema = 'tests'


class TestModel(Base):
    __tablename__ = 'test_migration'
    __table_args__ = {'schema': 'tests'}

    id: Mapped[int] = C(primary_key=True)
    data: Mapped[str] = C(String(128))
    create_date: Mapped[datetime] = C(DateTime(timezone=False), server_default=func.now())

    __mapper_args__ = {'eager_defaults': True}
