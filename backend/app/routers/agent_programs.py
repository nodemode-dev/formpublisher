from fastapi import APIRouter

from app.services import agent_programs

router = APIRouter(prefix="/api/agent-programs", tags=["terminal"])


@router.get("")
def agent_program_status(fresh: bool = False) -> dict:
    return agent_programs.status(fresh)
