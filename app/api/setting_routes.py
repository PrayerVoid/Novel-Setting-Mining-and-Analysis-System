from flask import Blueprint, request, jsonify
from ..services.setting_service import setting_service

bp = Blueprint('settings', __name__, url_prefix='/api/novels')

@bp.route('/<int:novel_id>/chapters/<int:chapter_number>/extract', methods=['POST'])
def extract_settings(novel_id, chapter_number):
    try:
        setting_service.extract_and_update_settings(novel_id, chapter_number)
        return jsonify({"message": f"Settings for chapter {chapter_number} extracted and updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/extract_batch', methods=['POST'])
def extract_batch_settings(novel_id):
    try:
        data = request.get_json() or {}
        start = data.get('start')
        end = data.get('end')
        
        if not start or not end or start > end:
            return jsonify({"error": "Invalid range"}), 400
            
        results = []
        errors = []
        
        # Note: This is a synchronous blocking operation which might timeout for large ranges.
        # For a production system, use Celery or similar.
        for i in range(start, end + 1):
            try:
                setting_service.extract_and_update_settings(novel_id, i)
                results.append(i)
            except Exception as e:
                errors.append({"chapter": i, "error": str(e)})
                # 出现错误时终止后续提取，避免错误累积或持续失败
                break
        
        return jsonify({
            "message": f"Batch extraction completed. Success: {len(results)}, Failures: {len(errors)}",
            "successful_chapters": results,
            "errors": errors
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/chapters/<int:chapter_number>/settings', methods=['GET'])
def get_settings(novel_id, chapter_number):
    settings = setting_service.get_settings_at_chapter(novel_id, chapter_number)
    return jsonify(settings)

@bp.route('/<int:novel_id>/chapters/<int:chapter_number>/changes', methods=['GET'])
def get_setting_changes(novel_id, chapter_number):
    changes = setting_service.get_chapter_changes(novel_id, chapter_number)
    return jsonify(changes)

@bp.route('/<int:novel_id>/extract_to_chapter', methods=['POST'])
def extract_to_chapter(novel_id):
    """
    从第一个未提取的章节开始，批量提取设定直到指定的章节。
    """
    try:
        data = request.get_json() or {}
        end_chapter = data.get('end_chapter')
        
        if not end_chapter:
            return jsonify({"error": "end_chapter is required"}), 400
            
        result = setting_service.batch_extract_settings_to_chapter(novel_id, end_chapter)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/settings/rollback', methods=['POST'])
def rollback_settings(novel_id):
    try:
        data = request.get_json() or {}
        try:
            start = int(data.get('start'))
            end = int(data.get('end'))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid start or end chapter"}), 400
        
        if start > end:
            return jsonify({"error": "Invalid range"}), 400
            
        setting_service.batch_rollback_settings(novel_id, start, end)
        
        return jsonify({"message": f"Settings rolled back for chapters {start} to {end}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
