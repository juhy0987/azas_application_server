from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_repository
from app.repositories.sqlite_blocks import SQLiteBlockRepository

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


class BlockPatch(BaseModel):
  text: str | None = None
  url: str | None = None
  caption: str | None = None
  title: str | None = None


@router.patch("/{block_id}")
def patch_block(
  block_id: str,
  body: BlockPatch,
  repo: SQLiteBlockRepository = Depends(get_repository),
) -> dict[str, str]:
  """Update editable content fields of a block."""
  patch_data = body.model_dump(exclude_unset=True, exclude_none=True)
  if not patch_data:
    raise HTTPException(status_code=422, detail="No fields to update")
  if not repo.update_block(block_id, patch_data):
    raise HTTPException(status_code=404, detail="Block not found")
  return {"id": block_id}
