from abc import ABC, abstractmethod

from app.repositories.user import AbstractUserRepository
from app.repositories.friend import AbstractFriendRepository
from app.repositories.profile import AbstractProfileRepository
from app.repositories.message import AbstractMessageRepository
from app.repositories.conversation import AbstractConversationRepository

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.session import AsyncSessionLocal
from app.repositories.user import SqlAlchemyUserRepository
from app.repositories.friend import SqlAlchemyFriendRepository
from app.repositories.profile import SqlAlchemyProfileRepository
from app.repositories.message import SqlAlchemyMessageRepository
from app.repositories.conversation import SqlAlchemyConversationRepository


class AbstractUnitOfWork(ABC):
    users: AbstractUserRepository
    friends: AbstractFriendRepository
    profiles: AbstractProfileRepository
    messages: AbstractMessageRepository
    conversations: AbstractConversationRepository


    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self


    async def __aexit__(self, exc_type, exc, tb):
        await self.rollback()


    @abstractmethod
    async def commit(self): ...


    @abstractmethod
    async def rollback(self): ...


    @abstractmethod
    def savepoint(self):...

class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AsyncSession):
        self.session = session


    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.users = SqlAlchemyUserRepository(self.session)
        self.friends = SqlAlchemyFriendRepository(self.session)
        self.profiles = SqlAlchemyProfileRepository(self.session)
        self.messages = SqlAlchemyMessageRepository(self.session)
        self.conversations = SqlAlchemyConversationRepository(self.session)
        return self


    async def __aexit__(self, exc_type, exc, tb):
        await super().__aexit__(exc_type, exc, tb)


    async def commit(self):
        await self.session.commit()


    async def rollback(self):
        await self.session.rollback()


    def savepoint(self):
        return self.session.begin_nested()