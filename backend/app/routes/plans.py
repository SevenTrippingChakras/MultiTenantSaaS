from fastapi import APIRouter

from app import plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
async def list_plans():
    """The public plan catalog (tiers, token allowances, features)."""
    return {
        "plans": [
            {
                "name": p.name,
                "monthly_token_limit": p.monthly_token_limit,
                "features": sorted(p.features),
            }
            for p in plans.all_plans()
        ]
    }
