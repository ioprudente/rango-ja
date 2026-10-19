import json
from pathlib import Path
from datetime import datetime
from rango_ja.actions.base import ActionLog, ActionRecord

class JsonActionLog(ActionLog):
    def __init__(self, filepath: str = "data/actions.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    async def record(self, record: ActionRecord) -> None:
        # Se o arquivo não existir (porque o teste apagou), cria um novo
        if not self.filepath.exists():
            self.filepath.write_text("[]", encoding="utf-8")
            
        data = json.loads(self.filepath.read_text(encoding="utf-8"))
        
        record_dict = record.model_dump()
        record_dict["registrado_em"] = record_dict["registrado_em"].isoformat()
        data.append(record_dict)
        
        self.filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def list_by_cliente(self, cliente_id: str) -> list[ActionRecord]:
        if not self.filepath.exists():
            return []
        data = json.loads(self.filepath.read_text(encoding="utf-8"))
        return [ActionRecord(**r) for r in data if r["cliente_id"] == cliente_id]
