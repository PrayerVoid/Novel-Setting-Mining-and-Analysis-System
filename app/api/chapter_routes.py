from flask import Blueprint, request, jsonify
import json
from app.services.chapter_service import chapter_service
from app.services.setting_service import setting_service
from app.services.ai_service import ai_service

bp = Blueprint('chapters', __name__, url_prefix='/api/novels')

@bp.route('/<int:novel_id>/chapters/batch', methods=['POST'])
def batch_import_chapters(novel_id):
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "List of chapters expected"}), 400
    
    result = chapter_service.batch_import_chapters(novel_id, data)
    return jsonify(result)

@bp.route('/<int:novel_id>/chapters/batch_delete', methods=['POST'])
def batch_delete_chapters(novel_id):
    data = request.get_json()
    start_num = data.get('start')
    end_num = data.get('end')
    
    if start_num is None:
        return jsonify({"error": "Start chapter number is required"}), 400
        
    try:
        count = chapter_service.delete_chapters_range(novel_id, int(start_num), int(end_num) if end_num else None)
        return jsonify({"message": f"Deleted {count} chapters", "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/import_next', methods=['POST'])
def import_next_chapter(novel_id):
    try:
        # 1. Get current max chapter
        latest = chapter_service.get_latest_chapter(novel_id)
        next_num = 1
        if latest:
            next_num = latest['number'] + 1
        
        result = chapter_service.import_from_local_file(novel_id, next_num, next_num)
        
        if result.get('success_count', 0) > 0:
            return jsonify({
                "message": f"Chapter {next_num} imported successfully",
                "chapter": {"number": next_num} # Simplified response
            })
        else:
             return jsonify({"error": "Failed to import chapter or no more chapters"}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/chapters', methods=['GET'])
def get_chapters(novel_id):
    chapters = chapter_service.get_chapters(novel_id)
    latest_extracted = setting_service.get_latest_extracted_chapter(novel_id)
    
    for chap in chapters:
        if chap['number'] <= latest_extracted:
            chap['status'] = 'extracted'
        else:
            chap['status'] = 'not_extracted'
            
    return jsonify({
        "chapters": chapters,
        "latest_extracted_chapter": latest_extracted
    })

@bp.route('/<int:novel_id>/chapters/latest', methods=['DELETE'])
def delete_latest_chapter_endpoint(novel_id):
    # This endpoint is kept to avoid breaking old logic if needed, but new logic is in delete_latest_chapter_and_settings
    # First get the latest chapter to know its number
    latest_chapter = chapter_service.get_latest_chapter(novel_id)
    if not latest_chapter:
        return jsonify({"error": "No chapters found"}), 404
    
    # Note: This now only deletes the chapter, not settings.
    # The new POST endpoint handles both.
    success = chapter_service.delete_chapter(novel_id, latest_chapter['number'])
    if success:
        return jsonify({"message": f"Chapter {latest_chapter['number']} deleted"})
    else:
        return jsonify({"error": "Failed to delete chapter"}), 500

@bp.route('/<int:novel_id>/extract_next_settings', methods=['POST'])
def extract_next_settings(novel_id):
    try:
        latest_extracted = setting_service.get_latest_extracted_chapter(novel_id)
        next_chapter_num = latest_extracted + 1
        
        # Check if next chapter exists
        chapter_to_process = chapter_service.get_chapter_content(novel_id, next_chapter_num)
        if not chapter_to_process:
            return jsonify({"error": f"Chapter {next_chapter_num} not found or already the last one."}), 404

        # Run extraction
        setting_service.extract_and_update_settings(novel_id, next_chapter_num)
        
        return jsonify({
            "message": f"Settings for chapter {next_chapter_num} extracted successfully."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/chapters/delete_latest', methods=['POST'])
def delete_latest_chapter_and_settings(novel_id):
    try:
        # 1. Get the latest chapter number from the chapters table
        latest_chapter = chapter_service.get_latest_chapter(novel_id)
        if not latest_chapter:
            return jsonify({"error": "No chapters to delete."}), 404
        
        chapter_num_to_delete = latest_chapter['number']

        # 2. Delete settings from this chapter forward
        setting_service.delete_settings_from_chapter(novel_id, chapter_num_to_delete)

        # 3. Delete the chapter itself
        chapter_service.delete_chapter(novel_id, chapter_num_to_delete)
        
        return jsonify({"message": f"Chapter {chapter_num_to_delete} and its settings have been deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/chapters/batch_delete', methods=['POST'])
def batch_delete_chapters_and_settings(novel_id):
    data = request.get_json()
    start_chapter = data.get('start_chapter')

    try:
        latest_extracted = setting_service.get_latest_extracted_chapter(novel_id)
        if not start_chapter or start_chapter > latest_extracted:
            return jsonify({"error": "Invalid start chapter"}), 400

        # 1. Delete settings from start_chapter to latest_extracted
        for i in range(start_chapter, latest_extracted + 1):
             setting_service.delete_settings_from_chapter(novel_id, i)

        return jsonify({"message": f"Settings from chapter {start_chapter} to {latest_extracted} have been deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:novel_id>/chapters/<int:chapter_num>/content', methods=['GET'])
def get_chapter_content(novel_id, chapter_num):
    chapter = chapter_service.get_chapter_content(novel_id, chapter_num)
    if chapter is None:
        return jsonify({"error": "Chapter not found"}), 404
    
    response_data = {"content": chapter['content']}
    
    if chapter.get('conflict_result'):
        try:
            response_data['conflict_result'] = json.loads(chapter['conflict_result'])
        except:
            response_data['conflict_result'] = None
            
    return jsonify(response_data)

@bp.route('/<int:novel_id>/chapters/<int:chapter_num>/detect_conflicts', methods=['POST'])
def detect_conflicts(novel_id, chapter_num):
    prev_settings = setting_service.get_settings_at_chapter(novel_id, chapter_num - 1)
    chapter = chapter_service.get_chapter_content(novel_id, chapter_num)
    if not chapter:
        return jsonify({"error": "Chapter content not found"}), 404
        
    result = ai_service.detect_conflicts(prev_settings, chapter['content'])
    
    # Save result to database
    chapter_service.update_conflict_result(novel_id, chapter_num, result)
    
    return jsonify(result)

@bp.route('/<int:novel_id>/chapters/<int:chapter_num>/chat', methods=['POST'])
def chat_with_ai(novel_id, chapter_num):
    data = request.get_json()
    user_query = data.get('query')
    if not user_query:
        return jsonify({"error": "Query is required"}), 400

    prev_settings = setting_service.get_settings_at_chapter(novel_id, chapter_num - 1)
    chapter = chapter_service.get_chapter_content(novel_id, chapter_num)
    if not chapter:
        return jsonify({"error": "Chapter content not found"}), 404
        
    response = ai_service.chat_with_context(prev_settings, chapter['content'], user_query)
    return jsonify({"response": response})
