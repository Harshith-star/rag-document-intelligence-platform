from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> models.User | None:
        result = await self.db.execute(select(models.User).where(models.User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> models.User | None:
        result = await self.db.execute(select(models.User).where(models.User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, full_name: str | None = None) -> models.User:
        user = models.User(email=email, hashed_password=hashed_password, full_name=full_name)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_profile(self, user: models.User, full_name: str | None) -> models.User:
        if full_name is not None:
            user.full_name = full_name
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def bump_cache_version(self, user_id: int) -> int:
        """Atomically increment a user's cache_version. Called whenever a
        document is added/changed/removed so every previously-cached Redis
        key (which embeds the old version number) becomes unreachable —
        the next identical question is guaranteed to miss the cache and
        regenerate a fresh, up-to-date answer."""
        await self.db.execute(
            update(models.User).where(models.User.id == user_id).values(cache_version=models.User.cache_version + 1)
        )
        await self.db.commit()
        user = await self.get_by_id(user_id)
        return user.cache_version
