from flask import Blueprint, jsonify, request
from ..services.setting_service import setting_service

bp = Blueprint('visualization', __name__, url_prefix='/api/novels')

@bp.route('/<int:novel_id>/chapters/<int:chapter_number>/knowledge_graph', methods=['GET'])
def get_knowledge_graph(novel_id, chapter_number):
    # 从查询参数获取 n，默认值为 1
    n = request.args.get('n', default=1, type=int)

    settings = setting_service.get_settings_at_chapter(novel_id, chapter_number)
    
    # 使用新的范围查询服务
    if n > 1:
        changes = setting_service.get_changes_in_range(novel_id, chapter_number, n)
        updated_entity_names = changes.get('updated_entity_names', set())
    else: # 兼容旧的单章查询
        changes = setting_service.get_chapter_changes(novel_id, chapter_number)
        updated_entity_names = {e['name'] for e in changes.get('new_entities', [])}
        # Add entities with updated properties
        updated_entity_names.update(p['entity_name'] for p in changes.get('new_properties', []))
        # Add entities with updated relationships
        for r in changes.get('new_relationships', []):
            updated_entity_names.add(r['subject_name'])
            updated_entity_names.add(r['object_name'])

    nodes = []
    links = []
    
    # Entities as nodes
    for entity in settings.get('entities', []):
        is_new = entity['name'] in updated_entity_names
        nodes.append({
            "id": str(entity['id']),
            "name": entity['name'],
            "category": entity['type'],
            "properties": entity.get('properties', {}),
            "is_new": is_new,
            # 向前端传递 start_chapter_id 以便进行更灵活的过滤
            "start_chapter": entity.get('start_chapter_id') 
        })
    
    # Relationships as links
    for rel in settings.get('relationships', []):
        # 为了找到节点的数字ID，我们需要一个从实体名称到ID的映射
        # 注意：这里的实现有一个潜在问题，如果存在同名实体，映射会不准确。
        # 在当前数据模型下，我们假设实体名称是唯一的。
        nodes_map = {n['name']: n['id'] for n in nodes}
        source_id = nodes_map.get(rel['subject'])
        target_id = nodes_map.get(rel['object'])
        
        if source_id and target_id:
            links.append({
                "source": source_id,
                "target": target_id,
                "value": rel['relation']
            })
    
    return jsonify({
        "nodes": nodes,
        "links": links
    })

@bp.route('/<int:novel_id>/chapters/<int:chapter_number>/knowledge_graph/shortest_path', methods=['GET'])
def get_shortest_path(novel_id, chapter_number):
    """返回两实体之间的最短路径（节点ID列表与路径上的边）。
    支持通过 source_id / target_id 或 source_name / target_name 指定实体。
    可选参数 n 用于和 `get_knowledge_graph` 保持一致的范围查询。
    """
    # 支持和原接口相同的 n 参数
    n = request.args.get('n', default=1, type=int)

    settings = setting_service.get_settings_at_chapter(novel_id, chapter_number)
    if n > 1:
        changes = setting_service.get_changes_in_range(novel_id, chapter_number, n)
    else:
        changes = setting_service.get_chapter_changes(novel_id, chapter_number)

    nodes = []
    links = []

    for entity in settings.get('entities', []):
        nodes.append({
            "id": str(entity['id']),
            "name": entity['name'],
            "category": entity['type'],
            "properties": entity.get('properties', {}),
        })

    nodes_map = {n['name']: n['id'] for n in nodes}
    id_to_node = {n['id']: n for n in nodes}

    for rel in settings.get('relationships', []):
        source_id = nodes_map.get(rel['subject'])
        target_id = nodes_map.get(rel['object'])
        if source_id and target_id:
            links.append({
                "source": source_id,
                "target": target_id,
                "value": rel['relation']
            })

    # Resolve source/target from query params
    source_id = request.args.get('source_id') or None
    target_id = request.args.get('target_id') or None
    source_name = request.args.get('source_name') or None
    target_name = request.args.get('target_name') or None

    if not source_id and source_name:
        source_id = nodes_map.get(source_name)
    if not target_id and target_name:
        target_id = nodes_map.get(target_name)

    if not source_id or not target_id:
        return jsonify({"error": "需要指定 source_id/source_name 和 target_id/target_name 中的两项"}), 400

    # 构建邻接表（无向图，用于查找连接路径）
    adj = {}
    for n in nodes:
        adj[n['id']] = set()
    for l in links:
        adj[l['source']].add(l['target'])
        adj[l['target']].add(l['source'])

    # BFS 寻找最短路径
    from collections import deque
    q = deque()
    q.append(source_id)
    prev = {source_id: None}
    found = False
    while q:
        cur = q.popleft()
        if cur == target_id:
            found = True
            break
        for nb in adj.get(cur, []):
            if nb not in prev:
                prev[nb] = cur
                q.append(nb)

    if not found:
        return jsonify({"path_nodes": [], "path_links": [], "message": "未找到连接路径"}), 200

    # 回溯路径
    path = []
    cur = target_id
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path = list(reversed(path))

    # 从原始 links 中提取路径上的边（保持方向和 relation 名称）
    link_map = {(l['source'], l['target']): l for l in links}
    path_edges = []
    for i in range(len(path) - 1):
        a = path[i]
        b = path[i+1]
        if (a, b) in link_map:
            path_edges.append(link_map[(a, b)])
        elif (b, a) in link_map:
            # 如果只有反向边存在，仍然将其作为连接展示（保留原始方向）
            path_edges.append(link_map[(b, a)])
        else:
            # 没有直接对应关系时，使用占位信息
            path_edges.append({"source": a, "target": b, "value": None})

    return jsonify({
        "path_nodes": path,
        "path_links": path_edges
    })
