import sqlite3
import os
import subprocess
from pathlib import Path

class DataSource:
    def __init__(self):
        self.git_login_dir = Path.home() / 'git-hyper'
        if not self.git_login_dir.exists():
            self.git_login_dir.mkdir()

        db_name = self.git_login_dir / 'database.db'
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def current_account(self):
        self.cursor.execute('SELECT * FROM accounts WHERE active = 1')
        return self.cursor.fetchall()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                ssh_key_path TEXT NOT NULL,
                active BOOLEAN DEFAULT 0
            )
        ''')
        self.conn.commit()

    def create_account(self, name, email, ssh_key_path):
        try:
            # Primeiro, desativar todas as contas
            self.cursor.execute('UPDATE accounts SET active = 0')
            
            # Criar nova conta ativa
            self.cursor.execute('''
                INSERT INTO accounts (name, email, ssh_key_path, active)
                VALUES (?, ?, ?, 1)
            ''', (name, email, ssh_key_path))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_accounts(self):
        self.cursor.execute('SELECT * FROM accounts ORDER BY active DESC, name')
        return self.cursor.fetchall()

    def activate_account(self, user_id):
        try:
            # Desativar todas as contas
            self.cursor.execute('UPDATE accounts SET active = 0')
            # Ativar a conta selecionada
            self.cursor.execute('UPDATE accounts SET active = 1 WHERE id = ?', (user_id,))
            self.conn.commit()
            
            # Aplicar configurações Git
            account = self.get_account_by_id(user_id)
            if account:
                self._apply_git_config(account)
            return True
        except Exception as e:
            print(f"Erro ao ativar conta: {e}")
            return False

    def get_account_by_id(self, user_id):
        self.cursor.execute('SELECT * FROM accounts WHERE id = ?', (user_id,))
        return self.cursor.fetchone()

    def update_account(self, user_id, newname, newemail, ssh_key_path=None):
        try:
            if ssh_key_path:
                self.cursor.execute('''
                    UPDATE accounts
                    SET name = ?, email = ?, ssh_key_path = ?
                    WHERE id = ?
                ''', (newname, newemail, ssh_key_path, user_id))
            else:
                self.cursor.execute('''
                    UPDATE accounts
                    SET name = ?, email = ?
                    WHERE id = ?
                ''', (newname, newemail, user_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_account(self, user_id):
        try:
            self.cursor.execute('DELETE FROM accounts WHERE id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def _apply_git_config(self, account):
        """Aplica configurações Git e SSH para a conta ativa"""
        _, name, email, ssh_key_path, _ = account
        
        try:
            # Configurar Git global
            subprocess.run(['git', 'config', '--global', 'user.name', name], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', email], check=True)
            
            # Configurar SSH
            self._setup_ssh_config(ssh_key_path)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Erro ao aplicar configurações Git: {e}")
            return False

    def _setup_ssh_config(self, ssh_key_path):
        """Configura o SSH para usar a chave da conta ativa"""
        ssh_dir = Path.home() / '.ssh'
        ssh_config_path = ssh_dir / 'config'
        
        # Criar diretório .ssh se não existir
        if not ssh_dir.exists():
            ssh_dir.mkdir(mode=0o700)

        # Configuração SSH para GitHub
        ssh_config_content = f"""# Git Login Manager Configuration
Host github.com
    HostName github.com
    User git
    IdentityFile {ssh_key_path}
    IdentitiesOnly yes

Host *
    AddKeysToAgent yes
"""
        
        # Escrever configuração SSH
        with open(ssh_config_path, 'w') as f:
            f.write(ssh_config_content)
        
        # Definir permissões corretas
        ssh_config_path.chmod(0o600)

    def generate_ssh_key(self, name, email):
        """Gera uma nova chave SSH para a conta"""
        ssh_dir = Path.home() / '.ssh'
        if not ssh_dir.exists():
            ssh_dir.mkdir(mode=0o700)
        
        # Nome do arquivo da chave
        key_name = f"git-login-{name.lower().replace(' ', '-')}"
        key_path = ssh_dir / key_name
        
        try:
            # Gerar chave SSH
            subprocess.run([
                'ssh-keygen', 
                '-t', 'ed25519', 
                '-C', email,
                '-f', str(key_path),
                '-N', ''  # Sem passphrase
            ], check=True)

            return str(key_path)
        except subprocess.CalledProcessError as e:
            print(f"Erro ao gerar chave SSH: {e}")
            return None
    
    def set_default(self, ssh_key_path):
        # Iniciar o ssh-agent, se não estiver rodando
        subprocess.run(['eval', '$(ssh-agent -s)'], shell=True)
        # Adicionar a chave ao ssh-agent
        subprocess.run(['ssh-add', str(ssh_key_path)], check=True)

    def get_public_key(self, ssh_key_path):
        """Retorna a chave pública SSH"""
        pub_key_path = f"{ssh_key_path}.pub"
        try:
            with open(pub_key_path, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def close(self):
        self.conn.close()