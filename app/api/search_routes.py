from flask import Blueprint, jsonify, request
from ..services.setting_service import setting_service

bp = Blueprint('search', __name__, url_prefix='/api/search')

@bp.route('/entity_history', methods=['GET'])
def get_entity_history():
    novel_id = request.args.get('novel_id', type=int)
    entity_name = request.args.get('entity_name', type=str)
    start_chapter = request.args.get('start_chapter', type=int)
    end_chapter = request.args.get('end_chapter', type=int)

    if not all([novel_id, entity_name, start_chapter, end_chapter]):
        return jsonify({"error": "Missing required parameters"}), 400

    history = setting_service.get_entity_history_in_range(novel_id, entity_name, start_chapter, end_chapter)
    
    return jsonify(history)

@bp.route('/suggest', methods=['GET'])
def suggest_entities():
    novel_id = request.args.get('novel_id', type=int)
    query = request.args.get('query', type=str, default='')
    
    if not novel_id:
        return jsonify([])
        
    suggestions = setting_service.search_entities(novel_id, query)
    return jsonify(suggestions)
