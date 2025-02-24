from fastapi import APIRouter

from src.api.v1.email_routers import confirm_router, recovery_router
from src.settings import settings

emails_router = APIRouter(
    prefix=settings.api.emails,
    tags=["MAILER-V1"],
)

email_sub_routers = (
    confirm_router,
    recovery_router,
)

for router in email_sub_routers:
    emails_router.include_router(router)
