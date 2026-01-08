from typing import Dict, List, Any
from app.services import db_service
from app.services.ai_service import ai_service

class SettingService:
    """
    设定服务核心逻辑：负责设定的提取、版本控制和存储。
    """

    def get_settings_at_chapter(self, novel_id: int, chapter_number: int) -> Dict[str, Any]:
        """
        获取指定章节结束时的完整世界观设定。
        """
        if chapter_number <= 0:
            return {"entities": [], "relationships": []}

        chapters = db_service.execute_query(
            "SELECT id FROM chapters WHERE novel_id = ? AND number = ?", 
            (novel_id, chapter_number)
        )
        if not chapters:
            return {"entities": [], "relationships": []}
        
        target_chapter_id = chapters[0]['id']

        # 2. 查询有效实体
        entities_sql = """
            SELECT e.*, c.number as start_chapter_number
            FROM entities e
            JOIN chapters c ON e.start_chapter_id = c.id
            WHERE c.novel_id = ? 
            AND e.start_chapter_id <= ? 
            AND (e.end_chapter_id IS NULL OR e.end_chapter_id > ?)
        """
        entities = db_service.execute_query(entities_sql, (novel_id, target_chapter_id, target_chapter_id))

        # 3. 查询有效属性
        formatted_entities = []
        for entity in entities:
            props_sql = """
                SELECT p.key, p.value, c.number as start_chapter_number
                FROM properties p
                JOIN chapters c ON p.start_chapter_id = c.id
                WHERE p.entity_id = ? 
                AND p.start_chapter_id <= ? 
                AND (p.end_chapter_id IS NULL OR p.end_chapter_id > ?)
            """
            props = db_service.execute_query(props_sql, (entity['id'], target_chapter_id, target_chapter_id))
            
            props_dict = {p['key']: p['value'] for p in props}
            props_meta = {p['key']: p['start_chapter_number'] for p in props}
            
            formatted_entities.append({
                "id": entity['id'],
                "name": entity['name'],
                "type": entity['type'],
                "properties": props_dict,
                "start_chapter": entity['start_chapter_number'],
                "property_start_chapters": props_meta
            })

        # 4. 查询有效关系
        rels_sql = """
            SELECT r.*, c.number as start_chapter_number
            FROM relationships r
            JOIN chapters c ON r.start_chapter_id = c.id
            WHERE c.novel_id = ? 
            AND r.start_chapter_id <= ? 
            AND (r.end_chapter_id IS NULL OR r.end_chapter_id > ?)
        """
        relationships = db_service.execute_query(rels_sql, (novel_id, target_chapter_id, target_chapter_id))
        
        formatted_relationships = []
        for rel in relationships:
            formatted_relationships.append({
                "id": rel['id'],
                "subject": rel['subject_name'],
                "object": rel['object_name'],
                "relation": rel['relation'],
                "start_chapter": rel['start_chapter_number']
            })

        return {"entities": formatted_entities, "relationships": formatted_relationships}

    def get_entity_history_in_range(self, novel_id: int, entity_name: str, start_chapter: int, end_chapter: int) -> List[Dict[str, Any]]:
        """
        获取指定实体在章节范围内的设定变更历史。
        """
        # 1. Find the entity by name
        entities = db_service.execute_query(
            """
            SELECT e.id, e.type 
            FROM entities e
            JOIN chapters c ON e.start_chapter_id = c.id
            WHERE c.novel_id = ? AND e.name = ?
            """,
            (novel_id, entity_name)
        )
        if not entities:
            return []
        
        entity_id = entities[0]['id']
        entity_type = entities[0]['type']

        # 2. Get chapter IDs for the range
        chapters_sql = "SELECT id, number FROM chapters WHERE novel_id = ? AND number >= ? AND number <= ? ORDER BY number"
        chapters = db_service.execute_query(chapters_sql, (novel_id, start_chapter, end_chapter))
        chapter_id_map = {c['id']: c['number'] for c in chapters}
        chapter_ids = list(chapter_id_map.keys())

        if not chapter_ids:
            return []

        history = []

        # 3. Check for entity creation
        placeholders = ','.join('?' for _ in chapter_ids)
        creation_sql = f"SELECT start_chapter_id FROM entities WHERE id = ? AND start_chapter_id IN ({placeholders})"
        creation_events = db_service.execute_query(creation_sql, (entity_id, *chapter_ids))
        for event in creation_events:
            history.append({
                "chapter_number": chapter_id_map[event['start_chapter_id']],
                "change_type": "new_entity",
                "details": {"type": entity_type}
            })

        # 4. Check for property changes
        props_sql = f"""
            SELECT key, value, start_chapter_id 
            FROM properties 
            WHERE entity_id = ? AND start_chapter_id IN ({placeholders})
        """
        prop_changes = db_service.execute_query(props_sql, (entity_id, *chapter_ids))
        
        for prop in prop_changes:
            history.append({
                "chapter_number": chapter_id_map[prop['start_chapter_id']],
                "change_type": "property_change",
                "details": {"key": prop['key'], "value": prop['value']}
            })

        history.sort(key=lambda x: x['chapter_number'])
        return history

    def get_chapter_changes(self, novel_id: int, chapter_number: int) -> Dict[str, Any]:
        """
        获取指定章节发生的设定变更（新增、修改、失效）。
        """
        chapters = db_service.execute_query(
            "SELECT id FROM chapters WHERE novel_id = ? AND number = ?", 
            (novel_id, chapter_number)
        )
        if not chapters:
            return {"new_entities": [], "updated_properties": [], "new_relationships": [], "invalidated": []}
        
        target_chapter_id = chapters[0]['id']
        
        # 1. 新增实体
        new_entities = db_service.execute_query(
            """
            SELECT e.* 
            FROM entities e
            JOIN chapters c ON e.start_chapter_id = c.id
            WHERE c.novel_id = ? AND e.start_chapter_id = ?
            """,
            (novel_id, target_chapter_id)
        )
        
        # 2. 新增/修改属性
        new_props = db_service.execute_query(
            """
            SELECT p.*, e.name as entity_name 
            FROM properties p 
            JOIN entities e ON p.entity_id = e.id 
            WHERE p.start_chapter_id = ?
            """,
            (target_chapter_id,)
        )
        
        # 3. 新增关系
        new_rels = db_service.execute_query(
            """
            SELECT r.*
            FROM relationships r
            JOIN chapters c ON r.start_chapter_id = c.id
            WHERE c.novel_id = ? AND r.start_chapter_id = ?
            """,
            (novel_id, target_chapter_id)
        )
        
        # 4. 失效/被修改的旧设定
        invalidated_props = db_service.execute_query(
            """
            SELECT p.*, e.name as entity_name 
            FROM properties p 
            JOIN entities e ON p.entity_id = e.id 
            WHERE p.end_chapter_id = ?
            """,
            (target_chapter_id,)
        )
        
        invalidated_rels = db_service.execute_query(
            """
            SELECT r.*
            FROM relationships r
            WHERE r.novel_id = ? AND r.end_chapter_id = ?
            """,
            (novel_id, target_chapter_id)
        )
        
        return {
            "new_entities": [dict(e) for e in new_entities],
            "new_properties": [dict(p) for p in new_props],
            "new_relationships": [dict(r) for r in new_rels],
            "invalidated_properties": [dict(p) for p in invalidated_props],
            "invalidated_relationships": [dict(r) for r in invalidated_rels]
        }

    def extract_and_update_settings(self, novel_id: int, chapter_number: int):
        """
        核心流程：增量提取并更新设定。
        """
        print(f"\n[SettingService] 开始处理第 {chapter_number} 章设定...")

        current_chapters = db_service.execute_query(
            "SELECT id, content FROM chapters WHERE novel_id = ? AND number = ?", 
            (novel_id, chapter_number)
        )
        if not current_chapters:
            print("  错误：找不到章节")
            return
        current_chapter = current_chapters[0]
        current_chapter_id = current_chapter['id']
        content = current_chapter['content']

        old_settings = self.get_settings_at_chapter(novel_id, chapter_number - 1)
        print(f"  [Context] 上一章有效实体数: {len(old_settings['entities'])}")

        ai_result = ai_service.extract_settings_from_text(content, old_settings)
        new_settings_data = ai_result.get("new_settings", {})
        
        db_operations = []
        
        new_entities = new_settings_data.get("entities", [])
        
        for new_ent in new_entities:
            name = new_ent['name']
            ent_type = new_ent.get('type', 'unknown')
            new_props = new_ent.get('properties', {})

            existing_ent_rows = db_service.execute_query(
                """
                SELECT e.id FROM entities e
                JOIN chapters c ON e.start_chapter_id = c.id
                WHERE c.novel_id = ? AND e.name = ? 
                AND (e.end_chapter_id IS NULL OR e.end_chapter_id > ?)
                """,
                (novel_id, name, current_chapter_id)
            )
            
            entity_id = None
            
            if not existing_ent_rows:
                print(f"  [Action] 发现新实体: {name}")
                entity_id = db_service.execute_commit(
                    "INSERT INTO entities (novel_id, name, type, start_chapter_id) VALUES (?, ?, ?, ?)",
                    (novel_id, name, ent_type, current_chapter_id)
                )
            else:
                entity_id = existing_ent_rows[0]['id']

            for key, value in new_props.items():
                if isinstance(value, (dict, list)):
                    import json
                    value = json.dumps(value, ensure_ascii=False)
                else:
                    value = str(value)

                existing_props = db_service.execute_query(
                    """
                    SELECT id, value FROM properties 
                    WHERE entity_id = ? AND key = ? 
                    AND (end_chapter_id IS NULL OR end_chapter_id > ?)
                    """,
                    (entity_id, key, current_chapter_id)
                )
                
                should_insert = False
                
                if existing_props:
                    old_prop = existing_props[0]
                    if old_prop['value'] != value:
                        print(f"  [Change] {name}.{key}: {old_prop['value']} -> {value}")
                        db_operations.append({
                            "query": "UPDATE properties SET end_chapter_id = ? WHERE id = ?",
                            "params": (current_chapter_id, old_prop['id'])
                        })
                        should_insert = True
                else:
                    print(f"  [New Prop] {name}.{key} = {value}")
                    should_insert = True
                
                if should_insert:
                    db_operations.append({
                        "query": "INSERT INTO properties (entity_id, key, value, start_chapter_id) VALUES (?, ?, ?, ?)",
                        "params": (entity_id, key, value, current_chapter_id)
                    })

        new_relationships = new_settings_data.get("relationships", [])
        for new_rel in new_relationships:
            subj = new_rel.get('subject')
            obj = new_rel.get('object')
            relation = new_rel.get('relation')
            
            if not subj or not obj or not relation:
                continue
                
            existing_rels = db_service.execute_query(
                """
                SELECT r.id, r.relation 
                FROM relationships r
                JOIN chapters c ON r.start_chapter_id = c.id
                WHERE c.novel_id = ? AND r.subject_name = ? AND r.object_name = ? 
                AND (r.end_chapter_id IS NULL OR r.end_chapter_id > ?)
                """,
                (novel_id, subj, obj, current_chapter_id)
            )
            
            should_insert = False
            if existing_rels:
                old_rel = existing_rels[0]
                if old_rel['relation'] != relation:
                    print(f"  [Change Rel] {subj} -> {obj}: {old_rel['relation']} -> {relation}")
                    db_operations.append({
                        "query": "UPDATE relationships SET end_chapter_id = ? WHERE id = ?",
                        "params": (current_chapter_id, old_rel['id'])
                    })
                    should_insert = True
            else:
                print(f"  [New Rel] {subj} -> {obj}: {relation}")
                should_insert = True
                
            if should_insert:
                db_operations.append({
                    "query": "INSERT INTO relationships (novel_id, subject_name, object_name, relation, start_chapter_id) VALUES (?, ?, ?, ?, ?)",
                    "params": (novel_id, subj, obj, relation, current_chapter_id)
                })

        invalidated = ai_result.get("invalidated_settings", [])
        for item in invalidated:
            item_type = item.get("type")
            if item_type == "relationship":
                subj = item.get("subject")
                obj = item.get("object")
                relation = item.get("relation")
                
                existing_rels = db_service.execute_query(
                    """
                    SELECT r.id 
                    FROM relationships r
                    JOIN chapters c ON r.start_chapter_id = c.id
                    WHERE c.novel_id = ? AND r.subject_name = ? AND r.object_name = ? AND r.relation = ?
                    AND (r.end_chapter_id IS NULL OR r.end_chapter_id > ?)
                    """,
                    (novel_id, subj, obj, relation, current_chapter_id)
                )
                for rel in existing_rels:
                    print(f"  [Invalidate Rel] {subj} -> {obj}: {relation}")
                    db_operations.append({
                        "query": "UPDATE relationships SET end_chapter_id = ? WHERE id = ?",
                        "params": (current_chapter_id, rel['id'])
                    })
            
            elif item_type == "property":
                entity_name = item.get("entity")
                key = item.get("key")
                
                ents = db_service.execute_query(
                    "SELECT e.id FROM entities e JOIN chapters c ON e.start_chapter_id = c.id WHERE c.novel_id = ? AND e.name = ?", 
                    (novel_id, entity_name)
                )
                if ents:
                    entity_id = ents[0]['id']
                    existing_props = db_service.execute_query(
                        """
                        SELECT id FROM properties 
                        WHERE entity_id = ? AND key = ? 
                        AND (end_chapter_id IS NULL OR end_chapter_id > ?)
                        """,
                        (entity_id, key, current_chapter_id)
                    )
                    for prop in existing_props:
                        print(f"  [Invalidate Prop] {entity_name}.{key}")
                        db_operations.append({
                            "query": "UPDATE properties SET end_chapter_id = ? WHERE id = ?",
                            "params": (current_chapter_id, prop['id'])
                        })

        if db_operations:
            db_service.execute_transaction(db_operations)
            print(f"  [Success] 数据库更新完成，执行了 {len(db_operations)} 个操作。")
        else:
            print("  [Info] 没有检测到需要更新的设定。")

    def rollback_settings(self, novel_id: int, target_chapter_number: int):
        """
        回滚设定：删除 target_chapter_number 之后产生的所有设定变更。
        """
        chapters = db_service.execute_query(
            "SELECT id FROM chapters WHERE novel_id = ? AND number = ?", 
            (novel_id, target_chapter_number)
        )
        if not chapters:
            return
        target_chapter_id = chapters[0]['id']
        
        print(f"[SettingService] 回滚第 {target_chapter_number} 章 (ID: {target_chapter_id}) 的设定...")

        operations = []
        
        operations.append({
            "query": "DELETE FROM properties WHERE start_chapter_id = ?",
            "params": (target_chapter_id,)
        })
        operations.append({
            "query": "DELETE FROM entities WHERE start_chapter_id = ?",
            "params": (target_chapter_id,)
        })
        operations.append({
            "query": "DELETE FROM relationships WHERE start_chapter_id = ?",
            "params": (target_chapter_id,)
        })
        
        operations.append({
            "query": "UPDATE properties SET end_chapter_id = NULL WHERE end_chapter_id = ?",
            "params": (target_chapter_id,)
        })
        operations.append({
            "query": "UPDATE entities SET end_chapter_id = NULL WHERE end_chapter_id = ?",
            "params": (target_chapter_id,)
        })
        operations.append({
            "query": "UPDATE relationships SET end_chapter_id = NULL WHERE end_chapter_id = ?",
            "params": (target_chapter_id,)
        })
        
        db_service.execute_transaction(operations)
        print("  [Success] 设定回滚完成。")

    def delete_settings_from_chapter(self, novel_id: int, chapter_number: int):
        """
        删除指定章节及之后的所有设定变更。
        """
        chapters = db_service.execute_query(
            "SELECT id FROM chapters WHERE novel_id = ? AND number >= ?",
            (novel_id, chapter_number)
        )
        if not chapters:
            return

        chapter_ids = [c['id'] for c in chapters]
        
        operations = []
        for chapter_id in chapter_ids:
            operations.append({
                "query": "DELETE FROM entities WHERE start_chapter_id = ?",
                "params": (chapter_id,)
            })
            operations.append({
                "query": "DELETE FROM properties WHERE start_chapter_id = ?",
                "params": (chapter_id,)
            })
            operations.append({
                "query": "DELETE FROM relationships WHERE start_chapter_id = ?",
                "params": (chapter_id,)
            })
            operations.append({
                "query": "UPDATE entities SET end_chapter_id = NULL WHERE end_chapter_id = ?",
                "params": (chapter_id,)
            })
            operations.append({
                "query": "UPDATE properties SET end_chapter_id = NULL WHERE end_chapter_id = ?",
                "params": (chapter_id,)
            })
            operations.append({
                "query": "UPDATE relationships SET end_chapter_id = NULL WHERE end_chapter_id = ?",
                "params": (chapter_id,)
            })

        db_service.execute_transaction(operations)

    def get_latest_extracted_chapter(self, novel_id: int) -> int:
        """
        获取最新提取设定的章节号
        """
        max_entity_chapter = db_service.execute_query("SELECT MAX(c.number) as max_num FROM entities e JOIN chapters c ON e.start_chapter_id = c.id WHERE c.novel_id = ?", (novel_id,))
        max_prop_chapter = db_service.execute_query("SELECT MAX(c.number) as max_num FROM properties p JOIN chapters c ON p.start_chapter_id = c.id JOIN entities e ON p.entity_id = e.id WHERE c.novel_id = ?", (novel_id,))
        max_rel_chapter = db_service.execute_query("SELECT MAX(c.number) as max_num FROM relationships r JOIN chapters c ON r.start_chapter_id = c.id WHERE c.novel_id = ?", (novel_id,))

        max_num = 0
        if max_entity_chapter and max_entity_chapter[0]['max_num']:
            max_num = max(max_num, max_entity_chapter[0]['max_num'])
        if max_prop_chapter and max_prop_chapter[0]['max_num']:
            max_num = max(max_num, max_prop_chapter[0]['max_num'])
        if max_rel_chapter and max_rel_chapter[0]['max_num']:
            max_num = max(max_num, max_rel_chapter[0]['max_num'])
            
        return max_num

    def batch_extract_settings_to_chapter(self, novel_id: int, end_chapter_number: int) -> Dict[str, Any]:
        """
        从第一个未提取的章节开始，批量提取设定直到指定的章节。
        """
        from app.services.chapter_service import chapter_service

        last_extracted_chapter_query = """
            SELECT MAX(c.number) as max_num
            FROM chapters c
            WHERE c.novel_id = ? AND c.id IN (
                SELECT DISTINCT e.start_chapter_id FROM entities e JOIN chapters c ON e.start_chapter_id = c.id WHERE c.novel_id = ?
                UNION
                SELECT DISTINCT p.start_chapter_id FROM properties p JOIN entities e ON p.entity_id = e.id JOIN chapters c ON p.start_chapter_id = c.id WHERE c.novel_id = ?
                UNION
                SELECT DISTINCT r.start_chapter_id FROM relationships r JOIN chapters c ON r.start_chapter_id = c.id WHERE c.novel_id = ?
            )
        """
        result = db_service.execute_query(last_extracted_chapter_query, (novel_id, novel_id, novel_id, novel_id))
        
        last_extracted_num = result[0]['max_num'] if result and result[0]['max_num'] is not None else 0
        start_chapter_number = last_extracted_num + 1

        if start_chapter_number > end_chapter_number:
            return {
                "message": f"All chapters up to {end_chapter_number} have already been extracted. Nothing to do.",
                "start_chapter": start_chapter_number,
                "end_chapter": end_chapter_number,
                "successful_chapters": [],
                "errors": []
            }

        successful_chapters = []
        errors = []
        
        for chapter_num in range(start_chapter_number, end_chapter_number + 1):
            try:
                chapter_data = db_service.execute_query(
                    "SELECT id, content FROM chapters WHERE novel_id = ? AND number = ?",
                    (novel_id, chapter_num)
                )
                if not chapter_data:
                    print(f"  [Auto-Import] Chapter {chapter_num} not found, attempting to import.")
                    try:
                        import_result = chapter_service.import_from_local_file(novel_id, chapter_num, chapter_num)
                        if import_result.get('success_count', 0) == 0:
                            raise Exception(import_result.get('message', 'Failed to import chapter from local file.'))
                        print(f"  [Auto-Import] Chapter {chapter_num} imported successfully.")
                    except Exception as import_e:
                        errors.append({"chapter": chapter_num, "error": f"Auto-import failed: {str(import_e)}"})
                        continue

                self.extract_and_update_settings(novel_id, chapter_num)
                successful_chapters.append(chapter_num)
            except Exception as e:
                errors.append({"chapter": chapter_num, "error": str(e)})

        return {
            "message": f"Batch extraction completed from chapter {start_chapter_number} to {end_chapter_number}.",
            "successful_chapters": successful_chapters,
            "errors": errors
        }

    def get_changes_in_range(self, novel_id: int, end_chapter_number: int, n: int) -> Dict[str, Any]:
        """
        获取在最近 n 章内发生的设定变更（包括新增实体、属性变更、关系变更）。
        """
        start_chapter_number = max(1, end_chapter_number - n + 1)

        chapters_sql = "SELECT id FROM chapters WHERE novel_id = ? AND number >= ? AND number <= ? ORDER BY number"
        chapters = db_service.execute_query(chapters_sql, (novel_id, start_chapter_number, end_chapter_number))
        if not chapters:
            return {"updated_entity_names": set()}
        
        chapter_ids = [c['id'] for c in chapters]
        placeholders = ','.join('?' for _ in chapter_ids)

        # 1. New Entities
        new_entities_sql = f"""
            SELECT e.name 
            FROM entities e
            JOIN chapters c ON e.start_chapter_id = c.id
            WHERE c.novel_id = ? AND e.start_chapter_id IN ({placeholders})
        """
        new_entities = db_service.execute_query(new_entities_sql, (novel_id, *chapter_ids))
        updated_names = {e['name'] for e in new_entities}

        # 2. Updated Properties
        updated_props_sql = f"""
            SELECT e.name
            FROM properties p
            JOIN entities e ON p.entity_id = e.id
            WHERE p.start_chapter_id IN ({placeholders})
        """
        updated_props = db_service.execute_query(updated_props_sql, (*chapter_ids,))
        updated_names.update(p['name'] for p in updated_props)

        # 3. Updated Relationships
        updated_rels_sql = f"""
            SELECT subject_name, object_name
            FROM relationships
            WHERE start_chapter_id IN ({placeholders})
        """
        updated_rels = db_service.execute_query(updated_rels_sql, (*chapter_ids,))
        for rel in updated_rels:
            updated_names.add(rel['subject_name'])
            updated_names.add(rel['object_name'])
        
        return {"updated_entity_names": updated_names}

    def search_entities(self, novel_id: int, query: str) -> List[str]:
        """
        根据查询词模糊搜索实体名称。
        """
        if not query:
            return []
            
        sql = """
            SELECT DISTINCT e.name 
            FROM entities e
            JOIN chapters c ON e.start_chapter_id = c.id
            WHERE c.novel_id = ? AND e.name LIKE ? 
            ORDER BY length(e.name) ASC LIMIT 20
        """
        results = db_service.execute_query(sql, (novel_id, f"%{query}%"))
        return [r['name'] for r in results]

    def batch_rollback_settings(self, novel_id: int, start_chapter: int, end_chapter: int) -> Dict[str, Any]:
        """
        批量回滚设定：
        1. 删除起始章节在 [start_chapter, end_chapter] 范围内的设定。
        2. 将结束章节在 [start_chapter, end_chapter] 范围内的设定的结束章节状态更新回 NULL。
        """
        # 1. 获取范围内的章节ID
        chapters = db_service.execute_query(
            "SELECT id FROM chapters WHERE novel_id = ? AND number >= ? AND number <= ?",
            (novel_id, start_chapter, end_chapter)
        )
        
        if not chapters:
            return {"success": True, "message": "No chapters in range"}
            
        chapter_ids = [c['id'] for c in chapters]
        placeholders = ','.join(['?'] * len(chapter_ids))
        
        operations = []
        
        tables = ['relationships', 'properties', 'entities']
        
        # 2. 更新结束章节在范围内的设定 (恢复为未结束)
        for table in tables:
            operations.append({
                "query": f"UPDATE {table} SET end_chapter_id = NULL WHERE end_chapter_id IN ({placeholders})",
                "params": tuple(chapter_ids)
            })
            
        # 3. 删除起始章节在范围内的设定
        for table in tables:
            operations.append({
                "query": f"DELETE FROM {table} WHERE start_chapter_id IN ({placeholders})",
                "params": tuple(chapter_ids)
            })
            
        try:
            db_service.execute_transaction(operations)
            return {"success": True}
        except Exception as e:
            raise e

# 单例
setting_service = SettingService()
