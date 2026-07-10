from bson import ObjectId

from app.db import get_db


async def find_by_email(email: str) -> dict | None:
    return await get_db().users.find_one({"email": email})


async def find_by_id(user_id: str) -> dict | None:
    return await get_db().users.find_one({"_id": ObjectId(user_id)})


async def insert(doc: dict) -> str:
    result = await get_db().users.insert_one(doc)
    return str(result.inserted_id)
