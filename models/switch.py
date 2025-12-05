from app import db
from datetime import datetime
from sqlalchemy import Numeric

class Switch(db.Model):
    __tablename__ = 'switches'
    
    # Identificação e Status
    id = db.Column(db.Integer, primary_key=True)
    id_ativo = db.Column(db.String(50), unique=True, nullable=False)  # SW-0001
    nome_switch = db.Column(db.String(100), nullable=False)
    status_funcionamento = db.Column(db.String(50), nullable=False)  # Em produção, Inativo, Manutenção
    criticidade = db.Column(db.String(20), nullable=False)  # Alta, Média, Baixa
    ambiente = db.Column(db.String(50), nullable=False)  # Produção, Teste, Desenvolvimento
    
    # Localização Física
    unidade = db.Column(db.String(100), nullable=False)
    local_detalhado = db.Column(db.String(200))
    rack = db.Column(db.String(50))
    posicao_u = db.Column(db.String(20))
    ponto_referencia = db.Column(db.String(200))
    
    # Dados Técnicos
    fabricante = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    numero_serie = db.Column(db.String(100))
    tipo_switch = db.Column(db.String(50))  # Core, Acesso, Distribuição
    stack_id = db.Column(db.String(50))
    qtd_ports_utp = db.Column(db.Integer)
    ports_utp_usadas = db.Column(db.Integer)
    qtd_ports_fibra = db.Column(db.Integer)
    ports_fibra_usadas = db.Column(db.Integer)
    suporta_poe = db.Column(db.Boolean, default=False)
    qtd_ports_poe = db.Column(db.Integer)
    capacidade_backplane = db.Column(db.String(50))
    
    # Endereçamento e Rede
    ip_gestao = db.Column(db.String(15))
    mascara_gestao = db.Column(db.String(15))
    gateway_gestao = db.Column(db.String(15))
    vlan_gestao = db.Column(db.Integer)
    vlans_configuradas = db.Column(db.String(200))
    uplink_principal = db.Column(db.String(100))
    velocidade_uplink = db.Column(db.String(50))
    
    # Software, Configuração e Segurança
    versao_so_firmware = db.Column(db.String(100))
    data_ultimo_upgrade = db.Column(db.Date)
    backup_config = db.Column(db.Boolean, default=False)
    data_ultimo_backup = db.Column(db.Date)
    metodo_gestao = db.Column(db.String(100))  # SSH, HTTPS, Console
    telnet_habilitado = db.Column(db.Boolean, default=False)
    dot1x_habilitado = db.Column(db.Boolean, default=False)
    stp_habilitado = db.Column(db.Boolean, default=False)
    port_security = db.Column(db.Boolean, default=False)
    acl_gestao_resumo = db.Column(db.Text)
    ultima_revisao_seg = db.Column(db.Date)
    
    # Dados Administrativos e Financeiros
    fornecedor = db.Column(db.String(100))
    numero_nota_fiscal = db.Column(db.String(50))
    data_aquisicao = db.Column(db.Date)
    valor_aquisicao = db.Column(Numeric(10, 2))
    centro_custo = db.Column(db.String(100))
    numero_tombamento = db.Column(db.String(50))
    projeto_origem = db.Column(db.String(100))
    inicio_garantia = db.Column(db.Date)
    fim_garantia = db.Column(db.Date)
    contrato_suporte = db.Column(db.String(100))
    sla_fornecedor = db.Column(db.String(100))
    responsavel_tecnico = db.Column(db.String(100))
    
    # Controle e Gestão
    idade_meses = db.Column(db.Integer)
    proximo_upgrade_sugerido = db.Column(db.Date)
    proximo_refresh_tecnico = db.Column(db.Date)
    observacoes = db.Column(db.Text)
    
    # Metadados
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'id_ativo': self.id_ativo,
            'nome_switch': self.nome_switch,
            'status_funcionamento': self.status_funcionamento,
            'criticidade': self.criticidade,
            'ambiente': self.ambiente,
            'unidade': self.unidade,
            'local_detalhado': self.local_detalhado,
            'rack': self.rack,
            'posicao_u': self.posicao_u,
            'ponto_referencia': self.ponto_referencia,
            'fabricante': self.fabricante,
            'modelo': self.modelo,
            'numero_serie': self.numero_serie,
            'tipo_switch': self.tipo_switch,
            'stack_id': self.stack_id,
            'qtd_ports_utp': self.qtd_ports_utp,
            'ports_utp_usadas': self.ports_utp_usadas,
            'qtd_ports_fibra': self.qtd_ports_fibra,
            'ports_fibra_usadas': self.ports_fibra_usadas,
            'suporta_poe': self.suporta_poe,
            'qtd_ports_poe': self.qtd_ports_poe,
            'capacidade_backplane': self.capacidade_backplane,
            'ip_gestao': self.ip_gestao,
            'mascara_gestao': self.mascara_gestao,
            'gateway_gestao': self.gateway_gestao,
            'vlan_gestao': self.vlan_gestao,
            'vlans_configuradas': self.vlans_configuradas,
            'uplink_principal': self.uplink_principal,
            'velocidade_uplink': self.velocidade_uplink,
            'versao_so_firmware': self.versao_so_firmware,
            'data_ultimo_upgrade': self.data_ultimo_upgrade.isoformat() if self.data_ultimo_upgrade else None,
            'backup_config': self.backup_config,
            'data_ultimo_backup': self.data_ultimo_backup.isoformat() if self.data_ultimo_backup else None,
            'metodo_gestao': self.metodo_gestao,
            'telnet_habilitado': self.telnet_habilitado,
            'dot1x_habilitado': self.dot1x_habilitado,
            'stp_habilitado': self.stp_habilitado,
            'port_security': self.port_security,
            'acl_gestao_resumo': self.acl_gestao_resumo,
            'ultima_revisao_seg': self.ultima_revisao_seg.isoformat() if self.ultima_revisao_seg else None,
            'fornecedor': self.fornecedor,
            'numero_nota_fiscal': self.numero_nota_fiscal,
            'data_aquisicao': self.data_aquisicao.isoformat() if self.data_aquisicao else None,
            'valor_aquisicao': float(self.valor_aquisicao) if self.valor_aquisicao else None,
            'centro_custo': self.centro_custo,
            'numero_tombamento': self.numero_tombamento,
            'projeto_origem': self.projeto_origem,
            'inicio_garantia': self.inicio_garantia.isoformat() if self.inicio_garantia else None,
            'fim_garantia': self.fim_garantia.isoformat() if self.fim_garantia else None,
            'contrato_suporte': self.contrato_suporte,
            'sla_fornecedor': self.sla_fornecedor,
            'responsavel_tecnico': self.responsavel_tecnico,
            'idade_meses': self.idade_meses,
            'proximo_upgrade_sugerido': self.proximo_upgrade_sugerido.isoformat() if self.proximo_upgrade_sugerido else None,
            'proximo_refresh_tecnico': self.proximo_refresh_tecnico.isoformat() if self.proximo_refresh_tecnico else None,
            'observacoes': self.observacoes
        }
    
    def __repr__(self):
        return f'<Switch {self.id_ativo} - {self.nome_switch}>'