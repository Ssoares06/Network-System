from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from models.switch import Switch
from models.user import User
from models.data_dictionary import DataDictionary
import json
from datetime import datetime, timedelta
import openpyxl
from werkzeug.utils import secure_filename
import os

web_bp = Blueprint('web', __name__)

# Configurações para upload
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
UPLOAD_FOLDER = 'uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== ROTAS DE AUTENTICAÇÃO ==========

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('web.dashboard'))
        else:
            flash('Usuário ou senha inválidos', 'error')
    
    return render_template('login.html')

@web_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema', 'info')
    return redirect(url_for('web.login'))

@web_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        flash('Apenas administradores podem criar usuários', 'error')
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        is_admin = bool(request.form.get('is_admin'))
        
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe', 'error')
            return redirect(url_for('web.register'))
        
        user = User(
            username=username,
            email=email,
            name=name,
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Usuário criado com sucesso', 'success')
        return redirect(url_for('web.dashboard'))
    
    return render_template('register.html')

# ========== ROTAS PRINCIPAIS ==========

@web_bp.route('/')
@web_bp.route('/dashboard')
@login_required
def dashboard():
    # Estatísticas para o dashboard
    total_switches = Switch.query.count()
    switches_ativos = Switch.query.filter_by(status_funcionamento='Em produção').count()
    switches_alta_criticidade = Switch.query.filter_by(criticidade='Alta').count()
    
    # Distribuição por fabricante
    fabricantes = db.session.query(
        Switch.fabricante,
        db.func.count(Switch.id)
    ).group_by(Switch.fabricante).all()
    
    # Distribuição por status
    status_distribution = db.session.query(
        Switch.status_funcionamento,
        db.func.count(Switch.id)
    ).group_by(Switch.status_funcionamento).all()
    
    # Switches com garantia próxima do vencimento (30 dias)
    hoje = datetime.now().date()
    switches_garantia_proxima = Switch.query.filter(
        Switch.fim_garantia <= (hoje + timedelta(days=30)),
        Switch.fim_garantia >= hoje
    ).count()
    
    return render_template('dashboard.html',
                         total_switches=total_switches,
                         switches_ativos=switches_ativos,
                         switches_alta_criticidade=switches_alta_criticidade,
                         fabricantes=fabricantes,
                         switches_garantia_proxima=switches_garantia_proxima,
                         status_distribution=status_distribution)

@web_bp.route('/switches')
@login_required
def switches():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtros
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    criticidade = request.args.get('criticidade', '')
    
    query = Switch.query
    
    if search:
        query = query.filter(
            db.or_(
                Switch.id_ativo.ilike(f'%{search}%'),
                Switch.nome_switch.ilike(f'%{search}%'),
                Switch.local_detalhado.ilike(f'%{search}%')
            )
        )
    
    if status:
        query = query.filter(Switch.status_funcionamento == status)
    
    if criticidade:
        query = query.filter(Switch.criticidade == criticidade)
    
    switches = query.order_by(Switch.id_ativo).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('switches/list.html', switches=switches)

@web_bp.route('/switches/add', methods=['GET', 'POST'])
@login_required
def add_switch():
    if request.method == 'POST':
        try:
            # Processar campo fabricante (se for "Outro", usar o valor customizado)
            fabricante = request.form['fabricante']
            if fabricante == 'Outro':
                fabricante = request.form.get('fabricante_custom', 'Desconhecido')
            
            # Processar método_gestao (pode ser múltiplo)
            metodo_gestao = request.form.get('metodo_gestao')
            if isinstance(metodo_gestao, list):
                metodo_gestao = '; '.join(metodo_gestao)
            
            # Converter datas vazias para None
            def parse_date(date_str):
                if date_str:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                return None
            
            switch = Switch(
                # Identificação e Status
                id_ativo=request.form['id_ativo'],
                nome_switch=request.form['nome_switch'],
                status_funcionamento=request.form['status_funcionamento'],
                criticidade=request.form['criticidade'],
                ambiente=request.form['ambiente'],
                
                # Localização Física
                unidade=request.form['unidade'],
                local_detalhado=request.form.get('local_detalhado'),
                rack=request.form.get('rack'),
                posicao_u=request.form.get('posicao_u'),
                ponto_referencia=request.form.get('ponto_referencia'),
                
                # Dados Técnicos
                fabricante=fabricante,
                modelo=request.form['modelo'],
                numero_serie=request.form.get('numero_serie'),
                tipo_switch=request.form.get('tipo_switch'),
                stack_id=request.form.get('stack_id'),
                qtd_ports_utp=request.form.get('qtd_ports_utp', type=int) or None,
                ports_utp_usadas=request.form.get('ports_utp_usadas', type=int) or None,
                qtd_ports_fibra=request.form.get('qtd_ports_fibra', type=int) or None,
                ports_fibra_usadas=request.form.get('ports_fibra_usadas', type=int) or None,
                suporta_poe=bool(request.form.get('suporta_poe')),
                qtd_ports_poe=request.form.get('qtd_ports_poe', type=int) or None,
                capacidade_backplane=request.form.get('capacidade_backplane'),
                
                # Endereçamento e Rede
                ip_gestao=request.form.get('ip_gestao'),
                mascara_gestao=request.form.get('mascara_gestao'),
                gateway_gestao=request.form.get('gateway_gestao'),
                vlan_gestao=request.form.get('vlan_gestao', type=int) or None,
                vlans_configuradas=request.form.get('vlans_configuradas'),
                uplink_principal=request.form.get('uplink_principal'),
                velocidade_uplink=request.form.get('velocidade_uplink'),
                
                # Software e Configuração
                versao_so_firmware=request.form.get('versao_so_firmware'),
                data_ultimo_upgrade=parse_date(request.form.get('data_ultimo_upgrade')),
                backup_config=bool(request.form.get('backup_config')),
                data_ultimo_backup=parse_date(request.form.get('data_ultimo_backup')),
                metodo_gestao=metodo_gestao,
                telnet_habilitado=bool(request.form.get('telnet_habilitado')),
                dot1x_habilitado=bool(request.form.get('dot1x_habilitado')),
                stp_habilitado=bool(request.form.get('stp_habilitado')),
                port_security=bool(request.form.get('port_security')),
                acl_gestao_resumo=request.form.get('acl_gestao_resumo'),
                ultima_revisao_seg=parse_date(request.form.get('ultima_revisao_seg')),
                
                # Dados Administrativos
                fornecedor=request.form.get('fornecedor'),
                numero_nota_fiscal=request.form.get('numero_nota_fiscal'),
                data_aquisicao=parse_date(request.form.get('data_aquisicao')),
                valor_aquisicao=request.form.get('valor_aquisicao', type=float) or None,
                centro_custo=request.form.get('centro_custo'),
                numero_tombamento=request.form.get('numero_tombamento'),
                projeto_origem=request.form.get('projeto_origem'),
                inicio_garantia=parse_date(request.form.get('inicio_garantia')),
                fim_garantia=parse_date(request.form.get('fim_garantia')),
                contrato_suporte=request.form.get('contrato_suporte'),
                sla_fornecedor=request.form.get('sla_fornecedor'),
                responsavel_tecnico=request.form.get('responsavel_tecnico'),
                idade_meses=request.form.get('idade_meses', type=int) or None,
                proximo_upgrade_sugerido=parse_date(request.form.get('proximo_upgrade_sugerido')),
                proximo_refresh_tecnico=parse_date(request.form.get('proximo_refresh_tecnico')),
                observacoes=request.form.get('observacoes'),
                
                criado_por=current_user.id
            )
            
            db.session.add(switch)
            db.session.commit()
            
            flash('Switch cadastrado com sucesso!', 'success')
            return redirect(url_for('web.switches'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar switch: {str(e)}', 'error')
    
    return render_template('switches/add.html')

@web_bp.route('/switches/<int:id>')
@login_required
def view_switch(id):
    switch = Switch.query.get_or_404(id)
    return render_template('switches/view.html', switch=switch)

@web_bp.route('/switches/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_switch(id):
    switch = Switch.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Processar campo fabricante (se for "Outro", usar o valor customizado)
            fabricante = request.form['fabricante']
            if fabricante == 'Outro':
                fabricante = request.form.get('fabricante_custom', 'Desconhecido')
            
            # Processar método_gestao (pode ser múltiplo)
            metodo_gestao = request.form.get('metodo_gestao')
            if isinstance(metodo_gestao, list):
                metodo_gestao = '; '.join(metodo_gestao)
            
            # Converter datas vazias para None
            def parse_date(date_str):
                if date_str:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                return None
            
            # Atualizar todos os campos
            switch.id_ativo = request.form['id_ativo']
            switch.nome_switch = request.form['nome_switch']
            switch.status_funcionamento = request.form['status_funcionamento']
            switch.criticidade = request.form['criticidade']
            switch.ambiente = request.form['ambiente']
            switch.unidade = request.form['unidade']
            switch.local_detalhado = request.form.get('local_detalhado')
            switch.rack = request.form.get('rack')
            switch.posicao_u = request.form.get('posicao_u')
            switch.ponto_referencia = request.form.get('ponto_referencia')
            switch.fabricante = fabricante
            switch.modelo = request.form['modelo']
            switch.numero_serie = request.form.get('numero_serie')
            switch.tipo_switch = request.form.get('tipo_switch')
            switch.stack_id = request.form.get('stack_id')
            switch.qtd_ports_utp = request.form.get('qtd_ports_utp', type=int) or None
            switch.ports_utp_usadas = request.form.get('ports_utp_usadas', type=int) or None
            switch.qtd_ports_fibra = request.form.get('qtd_ports_fibra', type=int) or None
            switch.ports_fibra_usadas = request.form.get('ports_fibra_usadas', type=int) or None
            switch.suporta_poe = bool(request.form.get('suporta_poe'))
            switch.qtd_ports_poe = request.form.get('qtd_ports_poe', type=int) or None
            switch.capacidade_backplane = request.form.get('capacidade_backplane')
            switch.ip_gestao = request.form.get('ip_gestao')
            switch.mascara_gestao = request.form.get('mascara_gestao')
            switch.gateway_gestao = request.form.get('gateway_gestao')
            switch.vlan_gestao = request.form.get('vlan_gestao', type=int) or None
            switch.vlans_configuradas = request.form.get('vlans_configuradas')
            switch.uplink_principal = request.form.get('uplink_principal')
            switch.velocidade_uplink = request.form.get('velocidade_uplink')
            switch.versao_so_firmware = request.form.get('versao_so_firmware')
            switch.data_ultimo_upgrade = parse_date(request.form.get('data_ultimo_upgrade'))
            switch.backup_config = bool(request.form.get('backup_config'))
            switch.data_ultimo_backup = parse_date(request.form.get('data_ultimo_backup'))
            switch.metodo_gestao = metodo_gestao
            switch.telnet_habilitado = bool(request.form.get('telnet_habilitado'))
            switch.dot1x_habilitado = bool(request.form.get('dot1x_habilitado'))
            switch.stp_habilitado = bool(request.form.get('stp_habilitado'))
            switch.port_security = bool(request.form.get('port_security'))
            switch.acl_gestao_resumo = request.form.get('acl_gestao_resumo')
            switch.ultima_revisao_seg = parse_date(request.form.get('ultima_revisao_seg'))
            switch.fornecedor = request.form.get('fornecedor')
            switch.numero_nota_fiscal = request.form.get('numero_nota_fiscal')
            switch.data_aquisicao = parse_date(request.form.get('data_aquisicao'))
            switch.valor_aquisicao = request.form.get('valor_aquisicao', type=float) or None
            switch.centro_custo = request.form.get('centro_custo')
            switch.numero_tombamento = request.form.get('numero_tombamento')
            switch.projeto_origem = request.form.get('projeto_origem')
            switch.inicio_garantia = parse_date(request.form.get('inicio_garantia'))
            switch.fim_garantia = parse_date(request.form.get('fim_garantia'))
            switch.contrato_suporte = request.form.get('contrato_suporte')
            switch.sla_fornecedor = request.form.get('sla_fornecedor')
            switch.responsavel_tecnico = request.form.get('responsavel_tecnico')
            switch.idade_meses = request.form.get('idade_meses', type=int) or None
            switch.proximo_upgrade_sugerido = parse_date(request.form.get('proximo_upgrade_sugerido'))
            switch.proximo_refresh_tecnico = parse_date(request.form.get('proximo_refresh_tecnico'))
            switch.observacoes = request.form.get('observacoes')
            
            db.session.commit()
            flash('Switch atualizado com sucesso!', 'success')
            return redirect(url_for('web.view_switch', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar switch: {str(e)}', 'error')
    
    return render_template('switches/edit.html', switch=switch)

@web_bp.route('/import_switches', methods=['GET', 'POST'])
@login_required
def import_switches():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Criar diretório de upload se não existir
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Processar arquivo Excel
                workbook = openpyxl.load_workbook(filepath)
                sheet = workbook['Inventario Switches']
                
                imported = 0
                errors = []
                
                # Pular cabeçalho (linha 1) e começar da linha 2
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    try:
                        # Verificar se já existe pelo ID Ativo
                        if row[0] and Switch.query.filter_by(id_ativo=row[0]).first():
                            errors.append(f"Switch {row[0]} já existe")
                            continue
                        
                        switch = Switch(
                            # Identificação e Status
                            id_ativo=row[0] or f"SW-{Switch.query.count() + 1:04d}",
                            nome_switch=row[1] or 'Switch Sem Nome',
                            status_funcionamento=row[2] or 'Em produção',
                            criticidade=row[3] or 'Média',
                            ambiente=row[4] or 'Produção',
                            
                            # Localização Física
                            unidade=row[5] or 'Sede',
                            local_detalhado=row[6],
                            rack=row[7],
                            posicao_u=row[8],
                            ponto_referencia=row[9],
                            
                            # Dados Técnicos
                            fabricante=row[10] or 'Desconhecido',
                            modelo=row[11] or 'Desconhecido',
                            numero_serie=row[12],
                            tipo_switch=row[13],
                            stack_id=row[14],
                            qtd_ports_utp=row[15],
                            ports_utp_usadas=row[16],
                            qtd_ports_fibra=row[17],
                            ports_fibra_usadas=row[18],
                            suporta_poe=row[19] == 'Sim' if row[19] else False,
                            qtd_ports_poe=row[20],
                            capacidade_backplane=row[21],
                            
                            # Endereçamento e Rede
                            ip_gestao=row[22],
                            mascara_gestao=row[23],
                            gateway_gestao=row[24],
                            vlan_gestao=row[25],
                            vlans_configuradas=row[26],
                            uplink_principal=row[27],
                            velocidade_uplink=row[28],
                            
                            # Software e Configuração
                            versao_so_firmware=row[29],
                            data_ultimo_upgrade=row[30] if isinstance(row[30], datetime) else None,
                            backup_config=row[31] == 'Sim' if row[31] else False,
                            data_ultimo_backup=row[32] if isinstance(row[32], datetime) else None,
                            metodo_gestao=row[33],
                            telnet_habilitado=row[34] == 'Sim' if row[34] else False,
                            dot1x_habilitado=row[35] == 'Sim' if row[35] else False,
                            stp_habilitado=row[36] == 'Sim' if row[36] else False,
                            port_security=row[37] == 'Sim' if row[37] else False,
                            acl_gestao_resumo=row[38],
                            ultima_revisao_seg=row[39] if isinstance(row[39], datetime) else None,
                            
                            # Dados Administrativos
                            fornecedor=row[40],
                            numero_nota_fiscal=row[41],
                            data_aquisicao=row[42] if isinstance(row[42], datetime) else None,
                            valor_aquisicao=float(row[43]) if row[43] else None,
                            centro_custo=row[44],
                            numero_tombamento=row[45],
                            projeto_origem=row[46],
                            inicio_garantia=row[47] if isinstance(row[47], datetime) else None,
                            fim_garantia=row[48] if isinstance(row[48], datetime) else None,
                            contrato_suporte=row[49],
                            sla_fornecedor=row[50],
                            responsavel_tecnico=row[51],
                            idade_meses=row[52],
                            proximo_upgrade_sugerido=row[53] if isinstance(row[53], datetime) else None,
                            proximo_refresh_tecnico=row[54] if isinstance(row[54], datetime) else None,
                            observacoes=row[55],
                            
                            criado_por=current_user.id
                        )
                        
                        db.session.add(switch)
                        imported += 1
                        
                    except Exception as e:
                        errors.append(f"Erro na linha {row[0]}: {str(e)}")
                        continue
                
                db.session.commit()
                
                # Limpar arquivo temporário
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                if imported > 0:
                    flash(f'✅ {imported} switches importados com sucesso!', 'success')
                if errors:
                    flash(f'⚠️ {len(errors)} erros durante a importação. Verifique os dados.', 'warning')
                    for error in errors[:5]:  # Mostrar apenas os primeiros 5 erros
                        flash(error, 'error')
                
                return redirect(url_for('web.switches'))
                
            except Exception as e:
                flash(f'❌ Erro ao processar arquivo: {str(e)}', 'error')
                return redirect(request.url)
        
        else:
            flash('Tipo de arquivo não permitido. Use .xlsx ou .xls', 'error')
            return redirect(request.url)
    
    return render_template('switches/import.html')

@web_bp.route('/data-dictionary')
@login_required
def data_dictionary():
    dictionary = DataDictionary.query.filter_by(table_name='switches').order_by(DataDictionary.category, DataDictionary.column_name).all()
    
    # Agrupar por categoria
    categories = {}
    for item in dictionary:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
    
    return render_template('data_dictionary.html', categories=categories)

# ========== APIs ==========

@web_bp.route('/api/switches/<int:id>', methods=['DELETE'])
@login_required
def delete_switch(id):
    try:
        switch = Switch.query.get_or_404(id)
        db.session.delete(switch)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Switch excluído com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@web_bp.route('/api/init-system', methods=['POST'])
def init_system():
    """Inicializa o sistema com usuário admin padrão"""
    try:
        # Criar usuário admin se não existir
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@empresa.com',
                name='Administrador',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        
        return jsonify({'success': True, 'message': 'Sistema inicializado com usuário admin'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@web_bp.route('/api/init-dictionary', methods=['POST'])
@login_required
def init_dictionary():
    """Inicializa o dicionário de dados baseado no Excel"""
    try:
        # Limpar dados existentes
        DataDictionary.query.filter_by(table_name='switches').delete()
        
        # Dados do dicionário baseado no Excel
        dictionary_data = [
            # Identificação e Status
            {'column_name': 'id_ativo', 'data_type': 'string', 'description': 'Identificação para controle interno', 'required': True, 'max_length': 50, 'example': 'SW-0001', 'category': 'Identificação'},
            {'column_name': 'nome_switch', 'data_type': 'string', 'description': 'Nome do switch para identificação', 'required': True, 'max_length': 100, 'example': 'CORE-MATRIZ-01', 'category': 'Identificação'},
            {'column_name': 'status_funcionamento', 'data_type': 'string', 'description': 'Informa se equipamento está ativo em produção ou parado', 'required': True, 'max_length': 50, 'example': 'Em produção', 'category': 'Identificação'},
            {'column_name': 'criticidade', 'data_type': 'string', 'description': 'Nível de criticidade do equipamento', 'required': True, 'max_length': 20, 'example': 'Alta', 'category': 'Identificação'},
            {'column_name': 'ambiente', 'data_type': 'string', 'description': 'Ambiente onde o switch está instalado', 'required': True, 'max_length': 50, 'example': 'Produção', 'category': 'Identificação'},
            
            # Localização Física
            {'column_name': 'unidade', 'data_type': 'string', 'description': 'Unidade/local onde o switch está instalado', 'required': True, 'max_length': 100, 'example': 'Sede', 'category': 'Localização'},
            {'column_name': 'local_detalhado', 'data_type': 'string', 'description': 'Localização específica dentro da unidade', 'required': False, 'max_length': 200, 'example': 'CPD - Sala de Rede', 'category': 'Localização'},
            {'column_name': 'rack', 'data_type': 'string', 'description': 'Identificação do rack onde está instalado', 'required': False, 'max_length': 50, 'example': 'Rack-01', 'category': 'Localização'},
            {'column_name': 'posicao_u', 'data_type': 'string', 'description': 'Posição no rack em unidades U', 'required': False, 'max_length': 20, 'example': '20U', 'category': 'Localização'},
            {'column_name': 'ponto_referencia', 'data_type': 'string', 'description': 'Ponto de referência para localização', 'required': False, 'max_length': 200, 'example': 'Ao lado do firewall principal', 'category': 'Localização'},
            
            # Dados Técnicos
            {'column_name': 'fabricante', 'data_type': 'string', 'description': 'Fabricante do equipamento', 'required': True, 'max_length': 50, 'example': 'Cisco', 'category': 'Técnico'},
            {'column_name': 'modelo', 'data_type': 'string', 'description': 'Modelo específico do switch', 'required': True, 'max_length': 100, 'example': 'WS-C2960X-48FPS-L', 'category': 'Técnico'},
            {'column_name': 'numero_serie', 'data_type': 'string', 'description': 'Número de série do equipamento', 'required': False, 'max_length': 100, 'example': 'FOC1234X0AB', 'category': 'Técnico'},
            {'column_name': 'tipo_switch', 'data_type': 'string', 'description': 'Tipo/função do switch na rede', 'required': False, 'max_length': 50, 'example': 'Core', 'category': 'Técnico'},
            {'column_name': 'stack_id', 'data_type': 'string', 'description': 'Identificação do stack se aplicável', 'required': False, 'max_length': 50, 'example': 'Stack 1', 'category': 'Técnico'},
            {'column_name': 'qtd_ports_utp', 'data_type': 'integer', 'description': 'Quantidade total de portas UTP', 'required': False, 'max_length': None, 'example': '48', 'category': 'Técnico'},
            {'column_name': 'ports_utp_usadas', 'data_type': 'integer', 'description': 'Quantidade de portas UTP em uso', 'required': False, 'max_length': None, 'example': '40', 'category': 'Técnico'},
            {'column_name': 'qtd_ports_fibra', 'data_type': 'integer', 'description': 'Quantidade total de portas de fibra', 'required': False, 'max_length': None, 'example': '4', 'category': 'Técnico'},
            {'column_name': 'ports_fibra_usadas', 'data_type': 'integer', 'description': 'Quantidade de portas de fibra em uso', 'required': False, 'max_length': None, 'example': '2', 'category': 'Técnico'},
            {'column_name': 'suporta_poe', 'data_type': 'boolean', 'description': 'Indica se suporta Power over Ethernet', 'required': False, 'max_length': None, 'example': 'Sim', 'category': 'Técnico'},
            {'column_name': 'qtd_ports_poe', 'data_type': 'integer', 'description': 'Quantidade de portas PoE disponíveis', 'required': False, 'max_length': None, 'example': '24', 'category': 'Técnico'},
            {'column_name': 'capacidade_backplane', 'data_type': 'string', 'description': 'Capacidade total do backplane', 'required': False, 'max_length': 50, 'example': '216 Gbps', 'category': 'Técnico'},
            
            # Endereçamento e Rede
            {'column_name': 'ip_gestao', 'data_type': 'string', 'description': 'Endereço IP para gestão do switch', 'required': False, 'max_length': 15, 'example': '10.10.0.10', 'category': 'Rede'},
            {'column_name': 'mascara_gestao', 'data_type': 'string', 'description': 'Máscara de rede para gestão', 'required': False, 'max_length': 15, 'example': '255.255.255.0', 'category': 'Rede'},
            {'column_name': 'gateway_gestao', 'data_type': 'string', 'description': 'Gateway para gestão', 'required': False, 'max_length': 15, 'example': '10.10.0.1', 'category': 'Rede'},
            {'column_name': 'vlan_gestao', 'data_type': 'integer', 'description': 'VLAN utilizada para gestão', 'required': False, 'max_length': None, 'example': '99', 'category': 'Rede'},
            {'column_name': 'vlans_configuradas', 'data_type': 'string', 'description': 'Lista de VLANs configuradas no switch', 'required': False, 'max_length': 200, 'example': '10,20,30,40,50,99', 'category': 'Rede'},
            {'column_name': 'uplink_principal', 'data_type': 'string', 'description': 'Interface de uplink principal', 'required': False, 'max_length': 100, 'example': 'Te1/0/1; Te1/0/2', 'category': 'Rede'},
            {'column_name': 'velocidade_uplink', 'data_type': 'string', 'description': 'Velocidade do link de uplink', 'required': False, 'max_length': 50, 'example': '10 Gbps', 'category': 'Rede'},
            
            # Software e Configuração
            {'column_name': 'versao_so_firmware', 'data_type': 'string', 'description': 'Versão do SO/Firmware instalado', 'required': False, 'max_length': 100, 'example': '15.2(7)E7', 'category': 'Software'},
            {'column_name': 'data_ultimo_upgrade', 'data_type': 'date', 'description': 'Data do último upgrade de firmware', 'required': False, 'max_length': None, 'example': '15/03/2025', 'category': 'Software'},
            {'column_name': 'backup_config', 'data_type': 'boolean', 'description': 'Indica se backup de configuração existe', 'required': False, 'max_length': None, 'example': 'Sim', 'category': 'Software'},
            {'column_name': 'data_ultimo_backup', 'data_type': 'date', 'description': 'Data do último backup de configuração', 'required': False, 'max_length': None, 'example': '20/11/2025', 'category': 'Software'},
            {'column_name': 'metodo_gestao', 'data_type': 'string', 'description': 'Métodos de gestão habilitados', 'required': False, 'max_length': 100, 'example': 'SSH; HTTPS; Console', 'category': 'Software'},
            {'column_name': 'telnet_habilitado', 'data_type': 'boolean', 'description': 'Indica se Telnet está habilitado', 'required': False, 'max_length': None, 'example': 'Não', 'category': 'Software'},
            {'column_name': 'dot1x_habilitado', 'data_type': 'boolean', 'description': 'Indica se 802.1X está habilitado', 'required': False, 'max_length': None, 'example': 'Parcial', 'category': 'Software'},
            {'column_name': 'stp_habilitado', 'data_type': 'boolean', 'description': 'Indica se STP está habilitado', 'required': False, 'max_length': None, 'example': 'Sim', 'category': 'Software'},
            {'column_name': 'port_security', 'data_type': 'boolean', 'description': 'Indica se port security está habilitado', 'required': False, 'max_length': None, 'example': 'Parcial', 'category': 'Software'},
            {'column_name': 'acl_gestao_resumo', 'data_type': 'text', 'description': 'Resumo das ACLs de gestão configuradas', 'required': False, 'max_length': None, 'example': 'Acesso apenas da rede 10.10.0.0/24', 'category': 'Software'},
            {'column_name': 'ultima_revisao_seg', 'data_type': 'date', 'description': 'Data da última revisão de segurança', 'required': False, 'max_length': None, 'example': '01/09/2025', 'category': 'Software'},
            
            # Dados Administrativos
            {'column_name': 'fornecedor', 'data_type': 'string', 'description': 'Fornecedor do equipamento', 'required': False, 'max_length': 100, 'example': 'Distribuidor XYZ', 'category': 'Administrativo'},
            {'column_name': 'numero_nota_fiscal', 'data_type': 'string', 'description': 'Número da nota fiscal de aquisição', 'required': False, 'max_length': 50, 'example': 'NF 12345', 'category': 'Administrativo'},
            {'column_name': 'data_aquisicao', 'data_type': 'date', 'description': 'Data de aquisição do equipamento', 'required': False, 'max_length': None, 'example': '10/02/2023', 'category': 'Administrativo'},
            {'column_name': 'valor_aquisicao', 'data_type': 'decimal', 'description': 'Valor de aquisição do equipamento', 'required': False, 'max_length': None, 'example': '18500.00', 'category': 'Administrativo'},
            {'column_name': 'centro_custo', 'data_type': 'string', 'description': 'Centro de custo associado', 'required': False, 'max_length': 100, 'example': '01.01 - TI Corporativo', 'category': 'Administrativo'},
            {'column_name': 'numero_tombamento', 'data_type': 'string', 'description': 'Número de tombamento do patrimônio', 'required': False, 'max_length': 50, 'example': '22638', 'category': 'Administrativo'},
            {'column_name': 'projeto_origem', 'data_type': 'string', 'description': 'Projeto que originou a aquisição', 'required': False, 'max_length': 100, 'example': 'Projeto Rede 2023', 'category': 'Administrativo'},
            {'column_name': 'inicio_garantia', 'data_type': 'date', 'description': 'Data de início da garantia', 'required': False, 'max_length': None, 'example': '10/02/2023', 'category': 'Administrativo'},
            {'column_name': 'fim_garantia', 'data_type': 'date', 'description': 'Data de fim da garantia', 'required': False, 'max_length': None, 'example': '10/02/2026', 'category': 'Administrativo'},
            {'column_name': 'contrato_suporte', 'data_type': 'string', 'description': 'Identificação do contrato de suporte', 'required': False, 'max_length': 100, 'example': 'CSP-2023-45', 'category': 'Administrativo'},
            {'column_name': 'sla_fornecedor', 'data_type': 'string', 'description': 'SLA acordado com o fornecedor', 'required': False, 'max_length': 100, 'example': 'NBD On-site 8x5', 'category': 'Administrativo'},
            {'column_name': 'responsavel_tecnico', 'data_type': 'string', 'description': 'Responsável técnico pelo equipamento', 'required': False, 'max_length': 100, 'example': 'Contato do Fornecedor', 'category': 'Administrativo'},
            {'column_name': 'idade_meses', 'data_type': 'integer', 'description': 'Idade do equipamento em meses', 'required': False, 'max_length': None, 'example': '33', 'category': 'Administrativo'},
            {'column_name': 'proximo_upgrade_sugerido', 'data_type': 'date', 'description': 'Data sugerida para próximo upgrade', 'required': False, 'max_length': None, 'example': '01/06/2026', 'category': 'Administrativo'},
            {'column_name': 'proximo_refresh_tecnico', 'data_type': 'date', 'description': 'Data sugerida para refresh técnico', 'required': False, 'max_length': None, 'example': '01/01/2028', 'category': 'Administrativo'},
            {'column_name': 'observacoes', 'data_type': 'text', 'description': 'Observações gerais sobre o equipamento', 'required': False, 'max_length': None, 'example': 'Switch core responsável pela distribuição...', 'category': 'Administrativo'},
        ]
        
        # Inserir dados
        for item_data in dictionary_data:
            item = DataDictionary(
                table_name='switches',
                **item_data
            )
            db.session.add(item)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Dicionário de dados inicializado com {len(dictionary_data)} campos'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@web_bp.route('/api/switches/stats')
@login_required
def switches_stats():
    stats = {
        'total': Switch.query.count(),
        'ativos': Switch.query.filter_by(status_funcionamento='Em produção').count(),
        'inativos': Switch.query.filter(Switch.status_funcionamento != 'Em produção').count(),
        'alta_criticidade': Switch.query.filter_by(criticidade='Alta').count(),
        'por_fabricante': dict(db.session.query(Switch.fabricante, db.func.count(Switch.id)).group_by(Switch.fabricante).all()),
        'por_tipo': dict(db.session.query(Switch.tipo_switch, db.func.count(Switch.id)).group_by(Switch.tipo_switch).all())
    }
    return jsonify(stats)
# Adicione esta rota no arquivo web.py, junto com as outras rotas:

@web_bp.route('/assistant')
@login_required
def assistant():
    """Página do assistente inteligente"""
    return render_template('assistant.html')