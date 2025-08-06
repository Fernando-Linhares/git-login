#!/usr/bin/env python3
"""
Git Login Manager - Diagnóstico e Solução de Problemas
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path
import json

class GitLoginDoctor:
    def __init__(self):
        self.home_dir = Path.home()
        self.git_login_dir = self.home_dir / '.git-hyper'
        self.ssh_dir = self.home_dir / '.ssh'
        self.issues = []
        self.warnings = []
        
    def colored(self, text, color_code):
        """Adiciona cores ao texto"""
        return f"\033[{color_code}m{text}\033[0m"
    
    def check_installation(self):
        """Verifica se o Git Login Manager está instalado corretamente"""
        print("🔍 Verificando instalação...")
        
        # Verificar diretório principal
        if not self.git_login_dir.exists():
            self.issues.append("Diretório ~/.git-hyper não encontrado")
            return False
        
        # Verificar estrutura de arquivos
        app_dir = self.git_login_dir / 'app'
        if not app_dir.exists():
            self.issues.append("Diretório ~/.git-hyper/app não encontrado")
            return False
        
        datasource_file = app_dir / 'data_source.py'
        if not datasource_file.exists():
            self.issues.append("Arquivo data_source.py não encontrado")
            return False
        
        init_file = app_dir / '__init__.py'
        if not init_file.exists():
            self.issues.append("Arquivo __init__.py não encontrado")
            return False
        
        # Verificar executável
        executable = self.home_dir / '.local' / 'bin' / 'git-login'
        if not executable.exists():
            self.warnings.append("Executável git-login não encontrado em ~/.local/bin/")
        elif not os.access(executable, os.X_OK):
            self.issues.append("Executável git-login sem permissão de execução")
        
        print("✓ Instalação verificada")
        return True
    
    def check_dependencies(self):
        """Verifica dependências do sistema"""
        print("🔍 Verificando dependências...")
        
        # Verificar Python
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 6):
            self.issues.append(f"Python {python_version.major}.{python_version.minor} é muito antigo (requer 3.6+)")
        
        # Verificar Git
        try:
            result = subprocess.run(['git', '--version'], capture_output=True, text=True, check=True)
            git_version = result.stdout.strip()
            print(f"  ✓ {git_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.issues.append("Git não instalado ou não disponível no PATH")
        
        # Verificar SSH
        try:
            result = subprocess.run(['ssh', '-V'], capture_output=True, text=True, check=True)
            ssh_version = result.stderr.strip()  # SSH coloca versão no stderr
            print(f"  ✓ {ssh_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.issues.append("SSH não instalado ou não disponível no PATH")
        
        # Verificar ssh-keygen
        try:
            subprocess.run(['ssh-keygen', '--help'], capture_output=True, check=True)
            print("  ✓ ssh-keygen disponível")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.issues.append("ssh-keygen não disponível")
        
        print("✓ Dependências verificadas")
    
    def check_database(self):
        """Verifica integridade do banco de dados"""
        print("🔍 Verificando banco de dados...")
        
        db_path = self.git_login_dir / 'database.db'
        if not db_path.exists():
            self.warnings.append("Banco de dados não encontrado (será criado no primeiro uso)")
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar tabela accounts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
            if not cursor.fetchone():
                self.issues.append("Tabela 'accounts' não encontrada no banco de dados")
                conn.close()
                return
            
            # Verificar estrutura da tabela
            cursor.execute("PRAGMA table_info(accounts)")
            columns = cursor.fetchall()
            expected_columns = {'id', 'name', 'email', 'ssh_key_path', 'active'}
            actual_columns = {col[1] for col in columns}
            
            missing_columns = expected_columns - actual_columns
            if missing_columns:
                self.issues.append(f"Colunas faltando na tabela accounts: {missing_columns}")
            
            # Verificar dados
            cursor.execute("SELECT COUNT(*) FROM accounts")
            account_count = cursor.fetchone()[0]
            print(f"  ✓ {account_count} contas encontradas")
            
            # Verificar conta ativa
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE active = 1")
            active_count = cursor.fetchone()[0]
            
            if active_count == 0:
                self.warnings.append("Nenhuma conta ativa")
            elif active_count > 1:
                self.issues.append(f"Múltiplas contas ativas ({active_count}) - deve ter apenas 1")
            
            conn.close()
            
        except sqlite3.Error as e:
            self.issues.append(f"Erro no banco de dados: {e}")
        
        print("✓ Banco de dados verificado")
    
    def check_ssh_configuration(self):
        """Verifica configuração SSH"""
        print("🔍 Verificando configuração SSH...")
        
        # Verificar diretório .ssh
        if not self.ssh_dir.exists():
            self.warnings.append("Diretório ~/.ssh não existe")
            return
        
        # Verificar permissões do diretório .ssh
        ssh_perms = oct(self.ssh_dir.stat().st_mode)[-3:]
        if ssh_perms != '700':
            self.issues.append(f"Permissões incorretas em ~/.ssh ({ssh_perms}, deveria ser 700)")
        
        # Verificar arquivo config
        ssh_config = self.ssh_dir / 'config'
        if ssh_config.exists():
            config_perms = oct(ssh_config.stat().st_mode)[-3:]
            if config_perms not in ['600', '644']:
                self.issues.append(f"Permissões incorretas em ~/.ssh/config ({config_perms})")
            
            # Verificar conteúdo do config
            try:
                with open(ssh_config, 'r') as f:
                    content = f.read()
                
                if 'Git Login Manager' in content:
                    print("  ✓ Configuração SSH do Git Login Manager encontrada")
                else:
                    self.warnings.append("Configuração SSH não contém seção do Git Login Manager")
            except Exception as e:
                self.issues.append(f"Erro ao ler ~/.ssh/config: {e}")
        else:
            self.warnings.append("Arquivo ~/.ssh/config não encontrado")
        
        # Verificar chaves SSH do git-login
        git_login_keys = list(self.ssh_dir.glob('git-login-*'))
        if not git_login_keys:
            self.warnings.append("Nenhuma chave SSH do git-login encontrada")
        else:
            print(f"  ✓ {len(git_login_keys)} chaves SSH encontradas")
            
            # Verificar permissões das chaves
            for key_file in git_login_keys:
                key_perms = oct(key_file.stat().st_mode)[-3:]
                if key_file.suffix == '.pub':
                    if key_perms not in ['644', '600']:
                        self.warnings.append(f"Permissões da chave pública {key_file.name}: {key_perms}")
                else:
                    if key_perms != '600':
                        self.issues.append(f"Permissões da chave privada {key_file.name}: {key_perms} (deveria ser 600)")
        
        print("✓ Configuração SSH verificada")
    
    def check_git_configuration(self):
        """Verifica configuração global do Git"""
        print("🔍 Verificando configuração Git...")
        
        try:
            # Verificar user.name
            result = subprocess.run(['git', 'config', '--global', 'user.name'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                git_name = result.stdout.strip()
                print(f"  ✓ user.name: {git_name}")
            else:
                self.warnings.append("Git user.name não configurado")
            
            # Verificar user.email
            result = subprocess.run(['git', 'config', '--global', 'user.email'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                git_email = result.stdout.strip()
                print(f"  ✓ user.email: {git_email}")
            else:
                self.warnings.append("Git user.email não configurado")
                
        except Exception as e:
            self.issues.append(f"Erro ao verificar configuração Git: {e}")
        
        print("✓ Configuração Git verificada")
    
    def test_github_connection(self):
        """Testa conexão com GitHub"""
        print("🔍 Testando conexão com GitHub...")
        
        try:
            result = subprocess.run(['ssh', '-T', 'git@github.com', '-o', 'ConnectTimeout=10'], 
                                  capture_output=True, text=True, timeout=15)
            
            if "successfully authenticated" in result.stderr:
                # Extrair nome de usuário se possível
                stderr_lines = result.stderr.split('\n')
                for line in stderr_lines:
                    if "successfully authenticated" in line and "!" in line:
                        username = line.split('!')[0].split()[-1]
                        print(f"  ✓ Autenticado como: {username}")
                        break
                else:
                    print("  ✓ Conexão SSH com GitHub funcionando")
            else:
                self.issues.append("Falha na autenticação SSH com GitHub")
                print(f"    Saída: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.issues.append("Timeout na conexão SSH com GitHub")
        except Exception as e:
            self.issues.append(f"Erro ao testar conexão GitHub: {e}")
        
        print("✓ Conexão GitHub testada")
    
    def check_path_configuration(self):
        """Verifica configuração do PATH"""
        print("🔍 Verificando configuração PATH...")
        
        local_bin = str(self.home_dir / '.local' / 'bin')
        current_path = os.environ.get('PATH', '')
        
        if local_bin in current_path:
            print("  ✓ ~/.local/bin está no PATH")
        else:
            self.warnings.append("~/.local/bin não está no PATH")
            print("    Adicione ao seu ~/.bashrc ou ~/.zshrc:")
            print(f'    export PATH="$HOME/.local/bin:$PATH"')
        
        print("✓ Configuração PATH verificada")
    
    def generate_report(self):
        """Gera relatório de diagnóstico"""
        print("\n" + "="*60)
        print(self.colored("RELATÓRIO DE DIAGNÓSTICO", "93"))
        print("="*60)
        
        if not self.issues and not self.warnings:
            print(self.colored("✅ SISTEMA SAUDÁVEL", "92"))
            print("Nenhum problema encontrado!")
            return
        
        if self.issues:
            print(self.colored("❌ PROBLEMAS CRÍTICOS:", "91"))
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
            print()
        
        if self.warnings:
            print(self.colored("⚠️ AVISOS:", "93"))
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
            print()
        
        # Sugestões de correção
        if self.issues or self.warnings:
            print(self.colored("💡 SUGESTÕES:", "96"))
            
            if any("não instalado" in issue for issue in self.issues):
                print("  • Instale as dependências faltantes (git, ssh)")
            
            if any("Permissões" in issue for issue in self.issues):
                print("  • Execute: chmod 700 ~/.ssh && chmod 600 ~/.ssh/config ~/.ssh/git-login-*")
            
            if any("PATH" in warning for warning in self.warnings):
                print("  • Adicione ~/.local/bin ao PATH e reinicie o terminal")
            
            if any("GitHub" in issue for issue in self.issues):
                print("  • Verifique se a chave pública está adicionada no GitHub")
                print("  • Execute 'git-login' → 'Ver conta atual' para ver a chave pública")
            
            if any("banco de dados" in issue.lower() for issue in self.issues):
                print("  • Execute 'git-login' para recriar o banco de dados")
    
    def run_full_diagnosis(self):
        """Executa diagnóstico completo"""
        print(self.colored("🏥 GIT LOGIN MANAGER - DIAGNÓSTICO", "96"))
        print("="*50)
        print()
        
        self.check_installation()
        self.check_dependencies()
        self.check_database()
        self.check_ssh_configuration()
        self.check_git_configuration()
        self.check_path_configuration()
        self.test_github_connection()
        
        self.generate_report()

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Git Login Manager - Diagnóstico')
    parser.add_argument('--json', action='store_true', 
                       help='Saída em formato JSON')
    
    args = parser.parse_args()
    
    doctor = GitLoginDoctor()
    
    if args.json:
        # Executar diagnósticos silenciosamente para JSON
        import io
        import contextlib
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            doctor.run_full_diagnosis()
        
        # Gerar saída JSON
        result = {
            'status': 'healthy' if not doctor.issues else 'issues',
            'issues': doctor.issues,
            'warnings': doctor.warnings,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        print(json.dumps(result, indent=2))
    else:
        doctor.run_full_diagnosis()

if __name__ == '__main__':
    main()