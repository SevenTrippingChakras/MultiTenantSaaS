from fastapi import APIRouter, status

from app.core.deps import CurrentUser
from app.models.user import TokenOut, UserLogin, UserOut, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    return await auth_service.register(data)


@router.post("/login", response_model=TokenOut)
async def login(data: UserLogin):
    token = await auth_service.login(data)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "created_at": user["created_at"],
    }
