from os import getenv

from typing import List, Optional, Union
from datetime import date, datetime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, ForeignKey, SmallInteger, CHAR, Date, Uuid, BigInteger, func, Text, NullPool
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncResult
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.schema import FetchedValue

import asyncio


SCHEMA = "shmafiabot-rework"


class Base(DeclarativeBase):
    # __abstract__ = True
    __table_args__ = {"schema": SCHEMA}


class GroupChat(Base):
    __tablename__ = "group_chat"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str]


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    bot: Mapped[bool] = mapped_column(nullable=False, default=False)


class GroupUser(Base):
    __tablename__ = "group_user"

    id: Mapped[int] = mapped_column(primary_key=True, server_default=FetchedValue())
    user_id: Mapped[BigInteger] = mapped_column(ForeignKey(f"{SCHEMA}.{User.__tablename__}.id"))
    group_chat_id: Mapped[BigInteger] = mapped_column(ForeignKey(f"{SCHEMA}.{GroupChat.__tablename__}.id"))


class MentionGroup(Base):
    __tablename__ = "mention_group"

    id: Mapped[int] = mapped_column(primary_key=True, server_default=FetchedValue())
    name: Mapped[str] = mapped_column(nullable=False)
    group_chat_id: Mapped[BigInteger] = mapped_column(ForeignKey(f"{SCHEMA}.{GroupChat.__tablename__}.id"))
    inversed_affiliation: Mapped[bool] = mapped_column(server_default=FetchedValue())
    pings: Mapped[List[str]] = mapped_column(ARRAY(Text))

    group_chat: Mapped[GroupChat] = relationship()


class GroupAffiliation(Base):
    __tablename__ = "group_affiliation"

    id: Mapped[int] = mapped_column(primary_key=True, server_default=FetchedValue())
    mention_group_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.{MentionGroup.__tablename__}.id"))
    group_user_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.{GroupUser.__tablename__}.id"))


class RestrictedUser(Base):
    __tablename__ = "restricted_user"

    id: Mapped[int] = mapped_column(primary_key=True, server_default=FetchedValue())
    group_user_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.{User.__tablename__}.id"), nullable=False)


class Config(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(primary_key=True, server_default=FetchedValue())
    group_chat_id: Mapped[BigInteger] = mapped_column(ForeignKey(f"{SCHEMA}.{GroupChat.__tablename__}.id"))
    key: Mapped[str] = mapped_column(primary_key=True, nullable=False, server_default=FetchedValue())
    value: Mapped[str] = mapped_column(primary_key=True, nullable=False)

    group_chat: Mapped[GroupChat] = relationship()


engine = create_async_engine(getenv("DATABASE_URL"), echo=True, poolclass=NullPool)

Session = async_sessionmaker(bind=engine, expire_on_commit=False)

async def main():
    # async_session = async_sessionmaker(engine, expire_on_commit=False)
    from sqlalchemy import select, column
    # async with async_session as session:
    # async with AsyncSession(engine) as session:
    while True:
        async with Session() as session:
            stmt = select(GroupChat, Config).select_from(GroupChat, Config).join(Config, GroupChat.id == Config.group_chat_id)
            result = await session.scalars(stmt)

            for student in result:
                print(student.name)

            await asyncio.sleep(2)

        # await session.close()

        await asyncio.sleep(20)

    # while True:
    #     await asyncio.sleep(60)

asyncio.run(main())
