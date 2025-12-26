from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models import User, Wallet, Circle, Notification, AdminLog, ChatMessage
from app.core import security
from app.db.session import AsyncSessionLocal
from sqlmodel import select

class AdminAuth(AuthenticationBackend):
    """
    Custom Authentication Backend for SQLAdmin.
    Verifies user credentials and ensures verified admin role.
    """
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = form["username"], form["password"]

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalars().first()

        if not user or not security.verify_password(password, user.hashed_password):
            return False
        
        # Check if user is admin
        if user.role != "admin":
            return False

        request.session.update({"token": security.create_access_token(user.id)})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

class BaseAdminView(ModelView):
    """
    Base view for all admin models to enforce authentication and providing audit logging.
    """
    def is_accessible(self, request: Request) -> bool:
        return True

    def is_visible(self, request: Request) -> bool:
        return True

    async def after_model_change(self, data: dict, model: object, is_created: bool, request: Request):
        action = "create" if is_created else "update"
        await self._log_action(request, action, model)

    async def after_model_delete(self, model: object, request: Request):
        await self._log_action(request, "delete", model)

    async def _log_action(self, request: Request, action: str, model: object):
        # In a real app, we'd extract the admin ID from the session/token properly.
        # For now, we'll try to decode it or leave it generic if missing, 
        # but since we are authenticated, we should have a token.
        token = request.session.get("token")
        admin_id = None
        if token:
             # Basic decoding (ignoring expiration for simplicity of logging, or properly verify)
             # Ideally use security.py verify_token logic
             # This part requires decoding the JWT.
             pass
        
        # We need an admin_id for the log, let's assume we can get it or use a placeholder
        # For valid implementation we need to decode the token.
        from jose import jwt
        from app.core.config import settings
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
            admin_id = payload.get("sub")
        except:
             # If we can't get admin ID, maybe just log 'unknown' or fail?
             # But the model expects UUID.
             import uuid
             admin_id = uuid.UUID(int=0) # Nil UUID as fallback

        async with AsyncSessionLocal() as session:
            log = AdminLog(
                admin_id=admin_id,
                action=action,
                target_id=str(getattr(model, "id", "N/A")),
                target_model=model.__class__.__name__,
                ip_address=request.client.host,
                details=f"Admin action on {model.__class__.__name__}"
            )
            session.add(log)
            await session.commit()

class UserAdmin(BaseAdminView, model=User):
    """
    Admin view for User model.
    """
    column_list = [User.id, User.email, User.first_name, User.role, User.is_verified]
    column_searchable_list = [User.email, User.first_name, User.last_name]

class WalletAdmin(BaseAdminView, model=Wallet):
    """
    Admin view for Wallet model.
    """
    column_list = [Wallet.id, Wallet.user_id, Wallet.balance, Wallet.currency]

class CircleAdmin(BaseAdminView, model=Circle):
    """
    Admin view for Circle model.
    """
    column_list = [Circle.id, Circle.name, Circle.status, Circle.amount]

class NotificationAdmin(BaseAdminView, model=Notification):
    """
    Admin view for Notification model.
    """
    column_list = [Notification.id, Notification.user_id, Notification.title, Notification.type]

class AdminLogAdmin(ModelView, model=AdminLog):
    """
    Admin view for AdminLog model (Read-only).
    """
    column_list = [AdminLog.admin_id, AdminLog.action, AdminLog.target_model, AdminLog.timestamp]
    can_create = False
    can_edit = False
    can_delete = False

class ChatMessageAdmin(BaseAdminView, model=ChatMessage):
    """
    Admin view for ChatMessage model.
    """
    column_list = [ChatMessage.id, ChatMessage.circle_id, ChatMessage.user_id, ChatMessage.message_type, ChatMessage.timestamp]
    column_sortable_list = [ChatMessage.timestamp]
    column_default_sort = ("timestamp", True)

def setup_admin(app: FastAPI, engine: AsyncEngine):
    """
    Initializes SQLAdmin with the FastAPI app and SQLAlchemy engine.
    """
    from app.core.config import settings
    # Ensure SECRET_KEY is set for session
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(app, engine, authentication_backend=authentication_backend)
    
    admin.add_view(UserAdmin)
    admin.add_view(WalletAdmin)
    admin.add_view(CircleAdmin)
    admin.add_view(NotificationAdmin)
    admin.add_view(ChatMessageAdmin)
    admin.add_view(AdminLogAdmin)
