"""用户业务服务"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """用户服务"""

    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行 BCrypt 哈希"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict) -> str:
        """生成 JWT 访问令牌"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> dict | None:
        """解码 JWT 令牌"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def register(db: Session, data: UserCreate) -> User:
        """用户注册"""
        # 检查用户名是否已存在
        existing = db.query(User).filter(User.username == data.username).first()
        if existing:
            raise ValueError("用户名已存在")

        user = User(
            username=data.username,
            password_hash=UserService.hash_password(data.password),
            nickname=data.nickname or data.username,
            email=data.email,
            role=data.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, username: str, password: str) -> User:
        """用户登录验证"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise ValueError("用户名或密码错误")
        if user.status == 0:
            raise ValueError("账号已被禁用")
        if not UserService.verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def update_profile(db: Session, user_id: int, data: UserUpdate) -> User | None:
        """更新用户信息"""
        user = UserService.get_by_id(db, user_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_list(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        status: int | None = None,
    ) -> tuple[list[User], int]:
        """获取用户列表（分页）"""
        query = db.query(User)

        if role:
            query = query.filter(User.role == role)
        if status is not None:
            query = query.filter(User.status == status)

        total = query.count()
        users = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return users, total
