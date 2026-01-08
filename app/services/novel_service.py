from typing import List, Dict, Optional
from app.services import db_service

class NovelService:
    def create_novel(self, title: str, author: str) -> Dict:
        novel_id = db_service.execute_commit(
            "INSERT INTO novels (title, author) VALUES (?, ?)",
            (title, author)
        )
        return {"id": novel_id, "title": title, "author": author}

    def get_all_novels(self) -> List[Dict]:
        return db_service.execute_query("SELECT * FROM novels")

    def get_novel_details(self, novel_id: int) -> Optional[Dict]:
        novels = db_service.execute_query("SELECT * FROM novels WHERE id = ?", (novel_id,))
        return novels[0] if novels else None

    def delete_novel(self, novel_id: int) -> bool:
        # SQLite with foreign keys ON should handle cascade delete
        row_count = db_service.execute_commit("DELETE FROM novels WHERE id = ?", (novel_id,))
        return row_count > 0

novel_service = NovelService()
