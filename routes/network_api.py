from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from network_system_rag import network_system

network_api_bp = Blueprint('network_api', __name__)

@network_api_bp.route('/query', methods=['POST'])
@login_required
def query_system():
    """Endpoint para consultas no sistema inteligente"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'message': 'Por favor, forneça uma pergunta'
            })
        
        # Fazer consulta no sistema
        response = network_system.query(question, current_user.id)
        
        return jsonify({
            'success': True,
            'question': question,
            'response': response,
            'timestamp': network_system.last_update.isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro na consulta: {str(e)}'
        }), 500

@network_api_bp.route('/stats', methods=['GET'])
@login_required
def get_system_stats():
    """Endpoint para estatísticas do sistema"""
    try:
        # Atualizar estatísticas
        network_system.update_knowledge_base()
        
        return jsonify({
            'success': True,
            'initialized': network_system.initialized,
            'last_update': network_system.last_update.isoformat(),
            'message': 'Sistema de consultas inteligentes ativo'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter estatísticas: {str(e)}'
        }), 500