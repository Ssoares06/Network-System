# network_system_rag.py
import os
import re
from datetime import datetime, timedelta
from sqlalchemy import func, extract, or_, and_
from app import db
from models.switch import Switch

class NetworkRAGSystem:
    def __init__(self):
        self.initialized = True
        self.last_update = datetime.now()
        print("✅ Sistema RAG de Gestão de Rede inicializado")
    
    def natural_language_to_sql(self, question: str):
        """Converte linguagem natural em consultas SQL usando análise inteligente"""
        question_lower = question.lower().strip()
        
        # ANÁLISE INTELIGENTE DE INTENÇÃO
        filters = {
            "status": [],
            "localizacao": [], 
            "fabricante": [],
            "criticidade": [],
            "garantia_proxima": False,
            "valor_min": None,
            "valor_max": None,
            "ports_livres": False
        }
        aggregations = {
            "soma_valor": False,
            "contagem_switches": False,
            "agrupar_por": None,
            "mostrar_lista": True
        }
        
        # DETECÇÃO DE INTENÇÃO PRINCIPAL
        intencoes = {
            "contagem": any(palavra in question_lower for palavra in 
                           ['quantos', 'quantas', 'contagem', 'número', 'qtd', 'total']),
            "lista": any(palavra in question_lower for palavra in 
                        ['mostre', 'liste', 'exiba', 'mostrar', 'listar']),
            "valor": any(palavra in question_lower for palavra in 
                        ['valor', 'preço', 'custo', 'investimento', 'dinheiro']),
            "localizacao": any(palavra in question_lower for palavra in 
                              ['sede', 'filial', 'matriz', 'local', 'onde']),
            "status": any(palavra in question_lower for palavra in 
                         ['ativo', 'inativo', 'manutenção', 'funcionando', 'parado']),
            "garantia": any(palavra in question_lower for palavra in 
                           ['garantia', 'vencimento', 'vencer', 'validade']),
            "fabricante": any(palavra in question_lower for palavra in 
                             ['cisco', 'hp', 'dlink', 'tp-link', 'mikrotik', 'fabricante']),
            "ports": any(palavra in question_lower for palavra in 
                        ['portas', 'ports', 'conexões', 'livres', 'ocupadas'])
        }
        
        # STATUS - Análise contextual mais inteligente
        if 'inativo' in question_lower or 'manutenção' in question_lower or 'parado' in question_lower:
            filters["status"].extend(["Inativo", "Manutenção", "Inativo (Manutenção)"])
        elif 'ativo' in question_lower or 'produção' in question_lower or 'funcionando' in question_lower:
            filters["status"].extend(["Em produção", "Ativo"])
        
        # LOCALIZAÇÃO - Busca inteligente
        if 'sede' in question_lower or 'matriz' in question_lower:
            filters["localizacao"].extend(["Sede", "SEDE", "Matriz"])
        elif 'filial' in question_lower:
            filters["localizacao"].extend(["Filial", "Unidade"])
        
        # FABRICANTE - Detecção por substring
        fabricantes = ['cisco', 'hp', 'dlink', 'tp-link', 'mikrotik']
        for fabricante in fabricantes:
            if fabricante in question_lower:
                filters["fabricante"].append(fabricante.title())
        
        # GARANTIA - Detecção temporal
        if any(palavra in question_lower for palavra in ['garantia', 'vencimento', 'vencer']):
            filters["garantia_proxima"] = True
        
        # VALOR - Extração de números
        valor_match = re.search(r'valor.*?(\d+[\.,]?\d*)', question_lower)
        if valor_match:
            filters["valor_min"] = float(valor_match.group(1).replace(',', '.'))
        
        # PORTS - Detecção de capacidade
        if 'portas' in question_lower or 'ports' in question_lower:
            if 'livres' in question_lower or 'disponíveis' in question_lower:
                filters["ports_livres"] = True
        
        # AGRAGAÇÕES - Lógica inteligente
        if intencoes["contagem"] and not intencoes["lista"]:
            aggregations["contagem_switches"] = True
            aggregations["mostrar_lista"] = False
        
        if intencoes["valor"] and ('total' in question_lower or 'soma' in question_lower):
            aggregations["soma_valor"] = True
        
        if 'por fabricante' in question_lower or 'distribuição' in question_lower:
            aggregations["agrupar_por"] = "fabricante"
            aggregations["mostrar_lista"] = False
        
        return {"filters": filters, "aggregations": aggregations, "intentions": intencoes}
    
    def execute_rag_query(self, question: str):
        """Executa consulta inteligente no banco de dados"""
        try:
            # Análise da pergunta
            query_params = self.natural_language_to_sql(question)
            filters = query_params["filters"]
            aggregations = query_params["aggregations"]
            intentions = query_params["intentions"]
            
            # Construir query base
            query = Switch.query
            
            # APLICAÇÃO INTELIGENTE DE FILTROS
            conditions = []
            
            # Status
            if filters["status"]:
                conditions.append(Switch.status_funcionamento.in_(filters["status"]))
            
            # Localização
            if filters["localizacao"]:
                loc_conditions = []
                for local in filters["localizacao"]:
                    loc_conditions.append(Switch.unidade.ilike(f'%{local}%'))
                    loc_conditions.append(Switch.local_detalhado.ilike(f'%{local}%'))
                conditions.append(or_(*loc_conditions))
            
            # Fabricante
            if filters["fabricante"]:
                fab_conditions = [Switch.fabricante.ilike(f'%{fab}%') for fab in filters["fabricante"]]
                conditions.append(or_(*fab_conditions))
            
            # Garantia
            if filters["garantia_proxima"]:
                hoje = datetime.now().date()
                limite = hoje + timedelta(days=30)
                conditions.append(Switch.fim_garantia <= limite)
                conditions.append(Switch.fim_garantia >= hoje)
            
            # Valor
            if filters["valor_min"]:
                conditions.append(Switch.valor_aquisicao >= filters["valor_min"])
            
            # Portas livres
            if filters["ports_livres"]:
                conditions.append(Switch.qtd_ports_utp > Switch.ports_utp_usadas)
            
            # Aplicar todas as condições
            if conditions:
                query = query.filter(and_(*conditions))
            
            # EXECUÇÃO INTELIGENTE
            if aggregations["soma_valor"] or aggregations["contagem_switches"] or aggregations["agrupar_por"]:
                return self._execute_aggregation_query(query, aggregations, filters, question, intentions)
            else:
                switches = query.order_by(Switch.nome_switch).all()
                return self._format_switches_result(switches, question, filters, intentions)
                
        except Exception as e:
            return f"❌ Erro na consulta RAG: {str(e)}"
    
    def _execute_aggregation_query(self, query, aggregations, filters, original_question, intentions):
        """Executa consultas de agregação de forma inteligente"""
        results = [f"🎯 **RESULTADO PARA: '{original_question}'**\n"]
        
        # CONTAGEM
        if aggregations["contagem_switches"]:
            count = query.count()
            
            # Mensagem contextual
            if filters["status"]:
                status_msg = f" com status {', '.join(filters['status'])}"
            elif filters["fabricante"]:
                status_msg = f" da {', '.join(filters['fabricante'])}"
            elif filters["localizacao"]:
                status_msg = f" na {', '.join(filters['localizacao'])}"
            else:
                status_msg = ""
                
            results.append(f"📊 **Total de Switches{status_msg}**: {count}")
        
        # SOMA DE VALORES
        if aggregations["soma_valor"]:
            total_valor = db.session.query(func.sum(Switch.valor_aquisicao)).filter(
                Switch.id.in_([s.id for s in query.all()])
            ).scalar() or 0
            
            context_msg = ""
            if filters["status"]:
                context_msg = f" ({', '.join(filters['status'])})"
            elif filters["fabricante"]:
                context_msg = f" (Fabricante: {', '.join(filters['fabricante'])})"
                
            results.append(f"💰 **Valor Total{context_msg}**: R$ {total_valor:,.2f}")
        
        # AGRUPAMENTO POR FABRICANTE
        if aggregations["agrupar_por"] == "fabricante":
            fabricantes = db.session.query(
                Switch.fabricante,
                func.count(Switch.id),
                func.sum(Switch.valor_aquisicao)
            ).filter(
                Switch.id.in_([s.id for s in query.all()])
            ).group_by(Switch.fabricante).order_by(func.count(Switch.id).desc()).all()
            
            if fabricantes:
                results.append("\n🏭 **Distribuição por Fabricante:**")
                for fabricante, count, valor in fabricantes:
                    valor_str = f" | 💰 R$ {valor:,.2f}" if valor else ""
                    results.append(f"   • **{fabricante}**: {count} switches{valor_str}")
        
        # MOSTRAR LISTA SE SOLICITADO
        if aggregations["mostrar_lista"] and query.count() <= 10:  # Mostra lista se poucos resultados
            switches = query.limit(10).all()
            if switches:
                results.append("\n📋 **Switches Encontrados:**")
                for switch in switches:
                    status_icon = "🟢" if "produção" in switch.status_funcionamento else "🔴"
                    results.append(f"   {status_icon} **{switch.id_ativo}** - {switch.nome_switch}")
                    results.append(f"      🏭 {switch.fabricante} | 🏢 {switch.local_detalhado}")
                    results.append(f"      💰 R$ {switch.valor_aquisicao:,.2f} | 🔌 {switch.ports_utp_usadas}/{switch.qtd_ports_utp} ports")
        
        return "\n".join(results) if len(results) > 1 else "📭 Nenhum dado encontrado para a consulta"
    
    def _format_switches_result(self, switches, original_question, filters, intentions):
        """Formata resultado dos switches de forma inteligente"""
        if not switches:
            return f"📭 Nenhum switch encontrado para: '{original_question}'"
        
        resultado = [f"🎯 **RESULTADO PARA: '{original_question}'**\n"]
        
        # Informações contextuais
        filter_info = []
        if filters["status"]:
            filter_info.append(f"Status: {', '.join(filters['status'])}")
        if filters["fabricante"]:
            filter_info.append(f"Fabricante: {', '.join(filters['fabricante'])}")
        if filters["localizacao"]:
            filter_info.append(f"Local: {', '.join(filters['localizacao'])}")
        
        if filter_info:
            resultado.append(f"🔍 **Filtros aplicados**: {', '.join(filter_info)}")
        
        resultado.append(f"📊 **Total encontrado: {len(switches)} switches**\n")
        
        for switch in switches:
            # CORREÇÃO DO ERRO: Verificar se datas são None
            garantia_str = "N/A"
            if switch.fim_garantia:
                garantia_str = switch.fim_garantia.strftime('%d/%m/%Y')
                
                if filters["garantia_proxima"]:
                    dias_restantes = (switch.fim_garantia - datetime.now().date()).days
                    garantia_str += f" (⚠️ {dias_restantes} dias)"
            
            status_icon = "🟢" if "produção" in switch.status_funcionamento else "🔴"
            
            resultado.append(f"{status_icon} **{switch.id_ativo}** - {switch.nome_switch}")
            resultado.append(f"   🏭 {switch.fabricante} | 🏢 {switch.local_detalhado}")
            resultado.append(f"   📍 {switch.unidade} | 🏷️ {switch.criticidade}")
            resultado.append(f"   🔌 Portas: {switch.ports_utp_usadas}/{switch.qtd_ports_utp} | 💰 R$ {switch.valor_aquisicao:,.2f}")
            resultado.append(f"   📅 Garantia até: {garantia_str}")
            resultado.append("")
        
        return "\n".join(resultado)
    
    def query(self, question: str, user_id=None):
        """Sistema de consultas inteligentes verdadeiro"""
        try:
            question_lower = question.lower().strip()
            
            if question_lower in ['ajuda', 'help', '?', 'como usar']:
                return self._show_help()
            
            if question_lower in ['estatísticas', 'stats', 'dashboard']:
                return self._get_system_stats()
            
            # Consulta inteligente no banco de dados
            return self.execute_rag_query(question)
            
        except Exception as e:
            return f"❌ Erro na consulta RAG: {str(e)}"
    
    def _get_system_stats(self):
        """Estatísticas do sistema em tempo real"""
        try:
            total_switches = Switch.query.count()
            switches_ativos = Switch.query.filter(
                Switch.status_funcionamento.in_(["Em produção", "Ativo"])
            ).count()
            switches_inativos = Switch.query.filter(
                Switch.status_funcionamento.in_(["Inativo", "Manutenção"])
            ).count()
            
            total_valor = db.session.query(func.sum(Switch.valor_aquisicao)).scalar() or 0
            
            # Distribuição por fabricante
            fabricantes = db.session.query(
                Switch.fabricante,
                func.count(Switch.id)
            ).group_by(Switch.fabricante).order_by(func.count(Switch.id).desc()).all()
            
            stats = [
                "📊 **ESTATÍSTICAS DO SISTEMA - TEMPO REAL**",
                "",
                f"🔢 **Total de Switches**: {total_switches}",
                f"🟢 **Em Produção**: {switches_ativos}",
                f"🔴 **Inativos/Manutenção**: {switches_inativos}",
                f"💰 **Valor Total em Equipamentos**: R$ {total_valor:,.2f}",
                "",
                "🏭 **Distribuição por Fabricante:**"
            ]
            
            for fabricante, count in fabricantes:
                stats.append(f"   • {fabricante}: {count}")
            
            return "\n".join(stats)
            
        except Exception as e:
            return f"❌ Erro ao buscar estatísticas: {str(e)}"
    
    def _show_help(self):
        """Mostra ajuda do sistema inteligente"""
        help_text = """
🤖 **ASSISTENTE INTELIGENTE DE REDE - AJUDA**

💡 **PERGUNTE DE FORMA NATURAL:**

🔢 CONTAGENS:
• "Quantos switches temos?"
• "Quantos switches ativos?"
• "Quantos switches Cisco na sede?"

💰 VALORES:
• "Qual o valor total dos equipamentos?"
• "Quanto investimos em switches ativos?"
• "Valor dos equipamentos em manutenção"

🏭 FABRICANTES:
• "Switches Cisco"
• "Equipamentos HP ativos"
• "Quantos switches temos da D-Link?"

📍 LOCALIZAÇÃO:
• "Switches na sede"
• "Equipamentos nas filiais"
• "Mostre switches ativos na matriz"

⚠️ GARANTIA:
• "Garantias próximas do vencimento"
• "Equipamentos com garantia expirando"

📊 RELATÓRIOS:
• "Distribuição por fabricante"
• "Estatísticas do sistema"
• "Dashboard completo"

🎯 EXEMPLOS AVANÇADOS:
• "Mostre switches Cisco ativos na sede com garantia próxima"
• "Qual o investimento total em equipamentos HP?"
• "Quantos switches temos inativos por fabricante?"
• "Liste equipamentos com mais de 20 portas ocupadas"

💬 O sistema entende contexto e intenção!
"""
        return help_text.strip()

    def update_knowledge_base(self):
        """Atualiza base de conhecimento"""
        return self._get_system_stats()

# Instância global do sistema inteligente
network_system = NetworkRAGSystem()