from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import ApiKey, Workspace


def ensure_default_workspace(db: Session, settings: Settings) -> None:
    workspace = db.get(Workspace, settings.default_workspace_id)
    if workspace is None:
        workspace = Workspace(id=settings.default_workspace_id, name="Demo Workspace")
        db.add(workspace)

    api_key = db.query(ApiKey).filter(ApiKey.key == settings.effective_api_key).one_or_none()
    if api_key is None:
        key_name = "demo" if settings.demo_mode else "default"
        db.add(ApiKey(workspace_id=settings.default_workspace_id, key=settings.effective_api_key, name=key_name))

    db.commit()
