from rango_ja.actions.base import ActionLog, ActionRecord
from rango_ja.actions.jsonfile import append_json_list, read_json_list
from rango_ja.config import get_settings

class JsonActionLog(ActionLog):
    """Log de auditoria das ações executadas (reembolsos aprovados e escaladas)."""
    def __init__(self, filepath: str | None = None) -> None:
        self._filepath = filepath

    @property
    def filepath(self) -> str:
        return self._filepath or get_settings().actions_path

    async def record(self, record: ActionRecord) -> None:
        entry = record.model_dump(mode="json")
        append_json_list(self.filepath, entry)

    async def list_by_cliente(self, cliente_id: str) -> list[ActionRecord]:
        return [ActionRecord(**r) for r in read_json_list(self.filepath) if r["cliente_id"] == cliente_id]
