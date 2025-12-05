#!/usr/bin/env python3
"""
Script para inicializar o sistema de Gestão de Rede
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🚀 Iniciando Sistema de Gestão de Rede...")
    print("📋 Carregando módulos...")
    
    try:
        from app import create_app, db
        from models.user import User
        from models.data_dictionary import DataDictionary
        from network_system_rag import network_system
        
        print("✅ Módulos carregados com sucesso")
        print("🔧 Inicializando aplicação...")
        
        app = create_app()
        with app.app_context():
            print("🗄️  Criando tabelas...")
            db.create_all()
            
            print("👤 Verificando usuário admin...")
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
                print("✅ Usuário admin criado (senha: admin123)")
            else:
                print("✅ Usuário admin já existe")
            
            print("🤖 Inicializando sistema de consultas inteligentes...")
            # Inicializar sistema de consultas
            network_system.update_knowledge_base()
            
            print("📊 Atualizando base de conhecimento...")
            # Estatísticas iniciais
            from models.switch import Switch
            total_switches = Switch.query.count()
            
            print("=" * 50)
            print("📊 SISTEMA DE GESTÃO DE REDE - ESTATÍSTICAS")
            print("=" * 50)
            print(f"📈 Total de Switches: {total_switches}")
            print(f"👥 Usuários: {User.query.count()}")
            print(f"🤖 Sistema IA: ✅ Ativo")
            print("=" * 50)
            
            print("\n🎉 SISTEMA DE GESTÃO DE REDE INICIALIZADO COM SUCESSO!")
            print("✨ Funcionalidades disponíveis:")
            print("   • Cadastro completo de switches")
            print("   • Consultas inteligentes sobre rede")
            print("   • Gestão de garantias e contratos")
            print("   • Dashboard com métricas em tempo real")
            print("   • Controle de inventário completo")
            print("   • 🤖 Assistente inteligente com IA")
            print("\n🌐 Acesse: http://localhost:5000")
            print("👤 Login: admin / admin123")
            print("💡 Use o assistente para fazer perguntas sobre sua rede!")
                
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Verifique se todos os arquivos estão no lugar correto")
    except Exception as e:
        print(f"❌ Erro durante a inicialização: {e}")
        print("💡 Verifique a configuração do banco de dados")

if __name__ == '__main__':
    main()