from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, auth
from ..exceptions import UserAlreadyExistsError, InvalidCredentialsError
from ..logging_config import get_logger
from ..repositories.user_repository import UserRepository

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, email: str, password: str, full_name: str | None = None) -> models.User:
        existing = await self.repo.get_by_email(email)
        if existing:
            logger.warning("Registration failed: email already exists email=%s", email)
            raise UserAlreadyExistsError()
        user = await self.repo.create(email, auth.hash_password(password), full_name)
        logger.info("User registered user_id=%s email=%s", user.id, email)
        return user

    async def authenticate(self, email: str, password: str) -> models.User:
        user = await self.repo.get_by_email(email)
        if not user or not auth.verify_password(password, user.hashed_password):
            logger.warning("Login failed email=%s", email)
            raise InvalidCredentialsError()
        logger.info("User logged in user_id=%s email=%s", user.id, email)
        return user

    async def update_profile(self, user: models.User, full_name: str | None) -> models.User:
        updated = await self.repo.update_profile(user, full_name)
        logger.info("Profile updated user_id=%s", user.id)
        return updated
