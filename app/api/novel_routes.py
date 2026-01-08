from flask import Blueprint, request, jsonify
from ..services.novel_service import novel_service
from ..services.setting_service import setting_service
from ..services import db_service

bp = Blueprint('novels', __name__, url_prefix='/api/novels')

@bp.route('', methods=['POST'])
def create_novel():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
    
    novel = novel_service.create_novel(data['title'], data.get('author', ''))
    return jsonify(novel), 201

@bp.route('', methods=['GET'])
def get_novels():
    novels = novel_service.get_all_novels()
    return jsonify(novels)

@bp.route('/<int:novel_id>', methods=['DELETE'])
def delete_novel(novel_id):
    success = novel_service.delete_novel(novel_id)
    if success:
        return jsonify({"message": "Novel deleted successfully"})
    else:
        return jsonify({"error": "Novel not found"}), 404

@bp.route('/<int:novel_id>/density', methods=['GET'])
def get_novel_density(novel_id):
    """计算小说的设定密度"""
    try:
        # 获取小说的总字数
        chapters = db_service.execute_query(
            "SELECT content FROM chapters WHERE novel_id = ?", 
            (novel_id,)
        )
        
        total_words = 0
        for chapter in chapters:
            if chapter['content']:
                total_words += len(chapter['content'])
        
        # 获取实体数量
        entities_count = db_service.execute_query(
            "SELECT COUNT(DISTINCT id) as count FROM entities WHERE novel_id = ?",
            (novel_id,)
        )[0]['count']
        
        # 获取属性数量
        properties_count = db_service.execute_query(
            "SELECT COUNT(*) as count FROM properties p JOIN entities e ON p.entity_id = e.id WHERE e.novel_id = ?",
            (novel_id,)
        )[0]['count']
        
        # 获取关系数量
        relationships_count = db_service.execute_query(
            "SELECT COUNT(*) as count FROM relationships WHERE novel_id = ?",
            (novel_id,)
        )[0]['count']
        
        # 计算设定密度
        if total_words > 0:
            density = (entities_count + properties_count + relationships_count) / total_words
        else:
            density = 0
        
        return jsonify({
            "novel_id": novel_id,
            "density": round(density, 6),
            "entities_count": entities_count,
            "properties_count": properties_count,
            "relationships_count": relationships_count,
            "word_count": total_words
        })
        
    except Exception as e:
        return jsonify({"error": f"计算密度失败: {str(e)}"}), 500

@bp.route('/<int:novel_id>/frequent_patterns', methods=['GET'])
def get_frequent_patterns(novel_id):
    """获取小说的频繁子图模式"""
    try:
        # 获取模式数量参数，默认为5
        count = request.args.get('count', 5, type=int)
        
        # 获取最新的章节设定
        latest_chapter = db_service.execute_query(
            "SELECT MAX(number) as max_chapter FROM chapters WHERE novel_id = ?",
            (novel_id,)
        )
        
        if not latest_chapter or not latest_chapter[0]['max_chapter']:
            return jsonify([])
        
        latest_chapter_num = latest_chapter[0]['max_chapter']
        
        # 获取最新章节的设定
        settings = setting_service.get_settings_at_chapter(novel_id, latest_chapter_num)
        
        # 提取图模式（简化实现）
        patterns = extract_frequent_patterns(settings, count)
        
        return jsonify(patterns)
        
    except Exception as e:
        return jsonify({"error": f"分析图模式失败: {str(e)}"}), 500

def extract_frequent_patterns(settings, count=5):
    """使用FP-Growth算法提取频繁子图模式"""
    patterns = []
    
    entities = settings.get('entities', [])
    relationships = settings.get('relationships', [])
    
    if not relationships:
        return patterns
    
    # 使用FP-Growth算法挖掘频繁模式
    frequent_patterns = fp_growth_algorithm(relationships, entities, min_support=2)
    
    # 按支持度排序并取前count个
    sorted_patterns = sorted(frequent_patterns, key=lambda x: x["support"], reverse=True)
    top_patterns = sorted_patterns[:count]
    
    # 转换为图结构
    for pattern_data in top_patterns:
        # 创建图结构数据
        nodes = []
        edges = []
        
        # 根据模式类型构建图结构
        if pattern_data["pattern_type"] == "binary_relation":
            # 二元关系模式
            nodes = [
                {
                    "id": "subject",
                    "label": pattern_data["subject_type"],
                    "color": "#FF6B6B"
                },
                {
                    "id": "object", 
                    "label": pattern_data["object_type"],
                    "color": "#4ECDC4"
                }
            ]
            
            edges = [
                {
                    "from": "subject",
                    "to": "object",
                    "label": pattern_data["relation_type"],
                    "arrows": "to"
                }
            ]
        elif pattern_data["pattern_type"] == "complex_pattern":
            # 复杂模式（多个关系）
            nodes = pattern_data.get("nodes", [])
            edges = pattern_data.get("edges", [])
        
        patterns.append({
            "support": pattern_data["support"],
            "node_types": pattern_data.get("node_types", []),
            "nodes": nodes,
            "edges": edges,
            "examples": pattern_data.get("examples", [])[:5],  # 只显示前5个例子
            "pattern_type": pattern_data["pattern_type"]
        })
    
    return patterns

def fp_growth_algorithm(relationships, entities, min_support=2):
    """FP-Growth算法实现"""
    # 第一步：构建事务数据库
    transactions = []
    
    # 将每个关系转换为事务项
    for rel in relationships:
        subject = rel['subject']
        object_ = rel['object']
        relation_type = rel['relation']
        
        # 查找实体的类型
        subject_type = find_entity_type(entities, subject)
        object_type = find_entity_type(entities, object_)
        
        # 创建事务项：关系三元组
        transaction = [
            f"subject:{subject_type}",
            f"relation:{relation_type}", 
            f"object:{object_type}"
        ]
        transactions.append(transaction)
    
    # 第二步：构建FP-tree
    fp_tree = FPTree()
    
    # 统计项频度
    item_frequency = {}
    for transaction in transactions:
        for item in transaction:
            item_frequency[item] = item_frequency.get(item, 0) + 1
    
    # 过滤低频项
    frequent_items = {item: freq for item, freq in item_frequency.items() 
                     if freq >= min_support}
    
    # 按频度排序
    sorted_items = sorted(frequent_items.items(), key=lambda x: x[1], reverse=True)
    
    # 构建FP-tree
    for transaction in transactions:
        # 过滤并排序事务项
        filtered_transaction = [item for item in transaction if item in frequent_items]
        sorted_transaction = sorted(filtered_transaction, 
                                  key=lambda x: frequent_items[x], reverse=True)
        if sorted_transaction:
            fp_tree.insert_transaction(sorted_transaction)
    
    # 第三步：挖掘频繁模式
    patterns = mine_frequent_patterns(fp_tree, min_support, frequent_items)
    
    # 第四步：转换为图模式
    graph_patterns = convert_to_graph_patterns(patterns, relationships, entities)
    
    return graph_patterns

class FPTreeNode:
    """FP-tree节点"""
    def __init__(self, item, count=1):
        self.item = item
        self.count = count
        self.children = {}
        self.parent = None
        self.next = None  # 用于链表

class FPTree:
    """FP-tree数据结构"""
    def __init__(self):
        self.root = FPTreeNode(None)
        self.header_table = {}
    
    def insert_transaction(self, transaction):
        """插入事务到FP-tree"""
        current_node = self.root
        
        for item in transaction:
            if item in current_node.children:
                current_node.children[item].count += 1
            else:
                new_node = FPTreeNode(item, 1)
                new_node.parent = current_node
                current_node.children[item] = new_node
                
                # 更新头表
                if item in self.header_table:
                    last_node = self.header_table[item]
                    while last_node.next:
                        last_node = last_node.next
                    last_node.next = new_node
                else:
                    self.header_table[item] = new_node
            
            current_node = current_node.children[item]

def mine_frequent_patterns(fp_tree, min_support, frequent_items):
    """挖掘频繁模式"""
    patterns = []
    
    # 按频度升序处理每个项
    sorted_items = sorted(frequent_items.items(), key=lambda x: x[1])
    
    for item, _ in sorted_items:
        # 构建条件模式基
        conditional_pattern_base = []
        node = fp_tree.header_table[item]
        
        while node:
            prefix_path = []
            current = node.parent
            while current.item is not None:
                prefix_path.append(current.item)
                current = current.parent
            
            if prefix_path:
                conditional_pattern_base.append((prefix_path, node.count))
            
            node = node.next
        
        # 构建条件FP-tree
        conditional_fp_tree = FPTree()
        conditional_freq_items = {}
        
        for pattern, count in conditional_pattern_base:
            for item_in_pattern in pattern:
                conditional_freq_items[item_in_pattern] = \
                    conditional_freq_items.get(item_in_pattern, 0) + count
        
        # 过滤低频项
        conditional_freq_items = {item: freq for item, freq in conditional_freq_items.items() 
                                 if freq >= min_support}
        
        # 构建条件FP-tree
        for pattern, count in conditional_pattern_base:
            filtered_pattern = [item for item in pattern if item in conditional_freq_items]
            sorted_pattern = sorted(filtered_pattern, 
                                  key=lambda x: conditional_freq_items[x], reverse=True)
            for _ in range(count):
                conditional_fp_tree.insert_transaction(sorted_pattern)
        
        # 递归挖掘
        if conditional_freq_items:
            sub_patterns = mine_frequent_patterns(conditional_fp_tree, min_support, conditional_freq_items)
            for sub_pattern in sub_patterns:
                patterns.append([item] + sub_pattern)
        
        patterns.append([item])
    
    return patterns

def convert_to_graph_patterns(patterns, relationships, entities):
    """将频繁模式转换为图模式"""
    graph_patterns = []
    
    for pattern in patterns:
        if len(pattern) >= 3:  # 至少包含主体、关系、客体
            # 解析模式项
            subject_type = None
            relation_type = None
            object_type = None
            
            for item in pattern:
                if item.startswith("subject:"):
                    subject_type = item.split(":")[1]
                elif item.startswith("relation:"):
                    relation_type = item.split(":")[1]
                elif item.startswith("object:"):
                    object_type = item.split(":")[1]
            
            if subject_type and relation_type and object_type:
                # 计算支持度
                support = calculate_pattern_support(relationships, entities, 
                                                   subject_type, relation_type, object_type)
                
                # 收集例子
                examples = []
                for rel in relationships:
                    s_type = find_entity_type(entities, rel['subject'])
                    o_type = find_entity_type(entities, rel['object'])
                    if s_type == subject_type and o_type == object_type and rel['relation'] == relation_type:
                        examples.append({
                            "subject": rel['subject'],
                            "object": rel['object'],
                            "relation": rel['relation']
                        })
                
                graph_patterns.append({
                    "support": support,
                    "subject_type": subject_type,
                    "relation_type": relation_type,
                    "object_type": object_type,
                    "node_types": [subject_type, object_type],
                    "examples": examples,
                    "pattern_type": "binary_relation"
                })
    
    return graph_patterns

def calculate_pattern_support(relationships, entities, subject_type, relation_type, object_type):
    """计算模式支持度"""
    support = 0
    for rel in relationships:
        s_type = find_entity_type(entities, rel['subject'])
        o_type = find_entity_type(entities, rel['object'])
        if s_type == subject_type and o_type == object_type and rel['relation'] == relation_type:
            support += 1
    return support

def find_entity_type(entities, entity_name):
    """根据实体名称查找实体类型"""
    for entity in entities:
        if entity['name'] == entity_name:
            return entity.get('type', '未知')
    return '未知'
