from fastapi import APIRouter

from app.services import trash

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("")
def list_trash():
    return trash.list_entries()


@router.delete("")
def empty_trash():
    return trash.empty()


@router.post("/{entry}/restore")
def restore_entry(entry: str):
    return trash.restore(entry)


@router.delete("/{entry}")
def delete_entry(entry: str):
    return trash.delete(entry)
