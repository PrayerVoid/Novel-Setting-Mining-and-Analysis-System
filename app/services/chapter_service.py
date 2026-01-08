from typing import List, Dict, Optional
from app.services import db_service
from app.services.setting_service import setting_service

class ChapterService:
    def batch_import_chapters(self, novel_id: int, chapters_data: List[Dict]) -> Dict:
        operations = []
        for chapter in chapters_data:
            # Check if exists (simple check, can be improved)
            # For batch import, we might want to ignore duplicates or update
            # Here we assume simple insert
            operations.append({
                "query": "INSERT INTO chapters (novel_id, number, title, content) VALUES (?, ?, ?, ?)",
                "params": (novel_id, chapter['number'], chapter['title'], chapter['content'])
            })
        
        try:
            db_service.execute_transaction(operations)
            return {"success_count": len(chapters_data), "errors": []}
        except Exception as e:
            return {"success_count": 0, "errors": [str(e)]}

    def get_chapters(self, novel_id: int) -> List[Dict]:
        return db_service.execute_query("SELECT id, number, title FROM chapters WHERE novel_id = ? ORDER BY number", (novel_id,))

    def get_chapter_content(self, novel_id: int, chapter_number: int) -> Optional[Dict]:
        chapters = db_service.execute_query(
            "SELECT * FROM chapters WHERE novel_id = ? AND number = ?", 
            (novel_id, chapter_number)
        )
        return chapters[0] if chapters else None

    def update_conflict_result(self, novel_id: int, chapter_number: int, result: Dict) -> bool:
        import json
        result_json = json.dumps(result, ensure_ascii=False)
        count = db_service.execute_commit(
            "UPDATE chapters SET conflict_result = ? WHERE novel_id = ? AND number = ?",
            (result_json, novel_id, chapter_number)
        )
        return count > 0

    def get_latest_chapter(self, novel_id: int) -> Optional[Dict]:
        chapters = db_service.execute_query(
            "SELECT * FROM chapters WHERE novel_id = ? ORDER BY number DESC LIMIT 1", 
            (novel_id,)
        )
        return chapters[0] if chapters else None

    def delete_chapter(self, novel_id: int, chapter_number: int) -> bool:
        count = self.delete_chapters_range(novel_id, chapter_number, chapter_number)
        return count > 0

    def delete_chapters_range(self, novel_id: int, start_num: int, end_num: Optional[int] = None) -> int:
        # 1. Get IDs of chapters to delete
        if end_num:
            query = "SELECT id FROM chapters WHERE novel_id = ? AND number >= ? AND number <= ?"
            params = (novel_id, start_num, end_num)
        else:
            query = "SELECT id FROM chapters WHERE novel_id = ? AND number >= ?"
            params = (novel_id, start_num)
            
        chapters = db_service.execute_query(query, params)
        if not chapters:
            return 0
            
        chapter_ids = [c['id'] for c in chapters]
        placeholders = ','.join(['?'] * len(chapter_ids))
        
        operations = []
        
        # 2. Update end_chapter_id to NULL for records ending in these chapters
        # This "reopens" entities/relations that were closed in the deleted chapters
        for table in ['relationships', 'properties', 'entities']:
            operations.append({
                "query": f"UPDATE {table} SET end_chapter_id = NULL WHERE end_chapter_id IN ({placeholders})",
                "params": tuple(chapter_ids)
            })
            
        # 3. Delete records created in these chapters
        for table in ['relationships', 'properties', 'entities']:
            operations.append({
                "query": f"DELETE FROM {table} WHERE start_chapter_id IN ({placeholders})",
                "params": tuple(chapter_ids)
            })
            
        # 4. Delete the chapters themselves
        operations.append({
            "query": f"DELETE FROM chapters WHERE id IN ({placeholders})",
            "params": tuple(chapter_ids)
        })
        
        db_service.execute_transaction(operations)
        return len(chapter_ids)

    def import_from_local_file(self, novel_id: int, start_num: int, end_num: int) -> Dict:
        import os
        import sys
        
        # Add project root to sys.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        if project_root not in sys.path:
            sys.path.append(project_root)
            
        from utils.novel_splitter import split_novel_by_chapters
        
        # Get novel title from database
        novel = db_service.execute_query("SELECT title FROM novels WHERE id = ?", (novel_id,))
        if not novel:
            raise ValueError(f"Novel with id {novel_id} not found")
        title = novel[0]['title']
        
        # Find the corresponding novel file
        novel_file = self._find_novel_file(title, project_root)
        if not novel_file:
            raise FileNotFoundError(f"No novel file found for title '{title}'")
            
        all_chapters = split_novel_by_chapters(novel_file)
        
        chapters_to_import = []
        for i in range(start_num, end_num + 1):
            if i <= len(all_chapters):
                # 0-based index
                chapter_data = all_chapters[i - 1]
                chapter_data['number'] = i
                chapters_to_import.append(chapter_data)
        
        if not chapters_to_import:
            return {"success_count": 0, "message": "No chapters found in range"}
            
        return self.batch_import_chapters(novel_id, chapters_to_import)

    def _find_novel_file(self, title: str, project_root: str) -> Optional[str]:
        """
        根据小说标题尝试多种常见的文件名变体来查找小说文件。
        """
        import os
        # 清理标题，去掉书名号等
        clean_title = title.replace('《', '').replace('》', '').strip()
        
        # 尝试的候选文件名
        candidates = [
            f"{clean_title}.txt",
            f"《{clean_title}》.txt",
            f"{clean_title}小说.txt",
            f"{clean_title}全本.txt",
            f"{clean_title}完整版.txt",
            f"{clean_title}全集.txt",
            f"{title}.txt",  # 保持原标题
            f"{clean_title}（全本）.txt",
            f"{clean_title}(全本).txt",
            # 其他常见变体
            f"{clean_title}.TXT",  # 大写扩展名
        ]
        
        for candidate in candidates:
            path = os.path.join(project_root, candidate)
            if os.path.exists(path):
                return path
        
        return None

chapter_service = ChapterService()
