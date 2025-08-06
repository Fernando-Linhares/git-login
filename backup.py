#!/usr/bin/env python3
"""
Script para backup e restauração do Git Login Manager
"""

import os
import shutil
import sqlite3
import json
import tarfile
from datetime import datetime
from pathlib import Path
import argparse

class GitLoginBackup:
    def __init__(self):
        self.home_dir = Path.home()
        self.git_login_dir = self.home_dir / '.git-hyper'
        self.ssh_dir = self.home_dir / '.ssh'
        self.backup_dir = self.home_dir / '.git-hyper-backups'
        
    def create_backup(self, backup_name=None):
        """Cria backup completo das configurações"""
        
        if not self.git_login_dir.exists():
            print("❌ Git Login Manager não encontrado!")
            return False
            
        # Nome do backup
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"git-hyper-backup-{timestamp}"
            
        # Criar diretório de backup
        self.backup_dir.mkdir(exist_ok=True)
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        print(f"📦 Criando backup: {backup_path}")
        
        try:
            with tarfile.open(backup_path, 'w:gz') as tar:
                # Backup do diretório git-hyper
                if self.git_login_dir.exists():
                    tar.add(self.git_login_dir, arcname='git-hyper')
                    print("✓ Dados do Git Login Manager")
                
                # Backup das chaves SSH relacionadas
                ssh_keys = list(self.ssh_dir.glob('git-hyper-*'))
                if ssh_keys:
                    for key_file in ssh_keys:
                        tar.add(key_file, arcname=f"ssh-keys/{key_file.name}")
                    print(f"✓ {len(ssh_keys)} chaves SSH")
                
                # Backup do config SSH (apenas se contém configuração git-hyper)
                ssh_config = self.ssh_dir / 'config'
                if ssh_config.exists():
                    with open(ssh_config, 'r') as f:
                        content = f.read()
                    if 'Git Login Manager' in content:
                        tar.add(ssh_config, arcname='ssh-config/config')
                        print("✓ Configuração SSH")
                
                # Criar manifesto do backup
                manifest = self._create_manifest()
                manifest_path = self.git_login_dir / 'backup_manifest.json'
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
                tar.add(manifest_path, arcname='backup_manifest.json')
                manifest_path.unlink()  # Remove arquivo temporário
                
            print(f"✅ Backup criado com sucesso: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            print(f"❌ Erro ao criar backup: {e}")
            return None
    
    def _create_manifest(self):
        """Cria manifesto do backup com informações das contas"""
        manifest = {
            'backup_date': datetime.now().isoformat(),
            'version': '1.0',
            'accounts': []
        }
        
        db_path = self.git_login_dir / 'database.db'
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT id, name, email, ssh_key_path, active FROM accounts')
                
                for row in cursor.fetchall():
                    account = {
                        'id': row[0],
                        'name': row[1],
                        'email': row[2],
                        'ssh_key_path': row[3],
                        'active': bool(row[4])
                    }
                    manifest['accounts'].append(account)
                
                conn.close()
            except Exception as e:
                print(f"⚠️ Erro ao ler banco de dados para manifesto: {e}")
        
        return manifest
    
    def list_backups(self):
        """Lista backups disponíveis"""
        if not self.backup_dir.exists():
            print("📁 Nenhum backup encontrado.")
            return []
        
        backups = list(self.backup_dir.glob('git-hyper-backup-*.tar.gz'))
        if not backups:
            print("📁 Nenhum backup encontrado.")
            return []
        
        print("📋 Backups disponíveis:")
        print()
        
        backup_list = []
        for backup in sorted(backups, reverse=True):
            size = backup.stat().st_size / 1024  # KB
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            
            print(f"📦 {backup.name}")
            print(f"   Tamanho: {size:.1f} KB")
            print(f"   Data: {mtime.strftime('%d/%m/%Y %H:%M:%S')}")
            
            # Tentar extrair informações do manifesto
            try:
                with tarfile.open(backup, 'r:gz') as tar:
                    if 'backup_manifest.json' in tar.getnames():
                        manifest_file = tar.extractfile('backup_manifest.json')
                        manifest = json.load(manifest_file)
                        accounts_count = len(manifest.get('accounts', []))
                        print(f"   Contas: {accounts_count}")
            except:
                pass
            
            print()
            backup_list.append(str(backup))
        
        return backup_list
    
    def restore_backup(self, backup_path):
        """Restaura backup"""
        backup_file = Path(backup_path)
        if not backup_file.exists():
            print(f"❌ Arquivo de backup não encontrado: {backup_path}")
            return False
        
        print(f"🔄 Restaurando backup: {backup_file.name}")
        
        # Confirmar restauração
        response = input("⚠️ Isso irá sobrescrever as configurações atuais. Continuar? (s/N): ")
        if response.lower() != 's':
            print("❌ Restauração cancelada.")
            return False
        
        try:
            # Fazer backup das configurações atuais
            current_backup = self.create_backup(f"pre-restore-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            if current_backup:
                print(f"✓ Backup atual salvo em: {current_backup}")
            
            with tarfile.open(backup_file, 'r:gz') as tar:
                # Restaurar git-hyper directory
                git_login_members = [m for m in tar.getmembers() if m.name.startswith('git-hyper/')]
                if git_login_members:
                    # Remover diretório atual se existir
                    if self.git_login_dir.exists():
                        shutil.rmtree(self.git_login_dir)
                    
                    for member in git_login_members:
                        member.name = member.name.replace('git-hyper/', '.git-hyper/')
                        tar.extract(member, self.home_dir)
                    print("✓ Dados do Git Login Manager restaurados")
                
                # Restaurar chaves SSH
                ssh_key_members = [m for m in tar.getmembers() if m.name.startswith('ssh-keys/')]
                if ssh_key_members:
                    for member in ssh_key_members:
                        key_name = member.name.replace('ssh-keys/', '')
                        member.name = key_name
                        tar.extract(member, self.ssh_dir)
                        
                        # Definir permissões corretas
                        key_path = self.ssh_dir / key_name
                        if key_path.suffix != '.pub':  # Chave privada
                            key_path.chmod(0o600)
                        else:  # Chave pública
                            key_path.chmod(0o644)
                    
                    print(f"✓ {len(ssh_key_members)} chaves SSH restauradas")
                
                # Restaurar configuração SSH
                ssh_config_members = [m for m in tar.getmembers() if m.name.startswith('ssh-config/')]
                if ssh_config_members:
                    for member in ssh_config_members:
                        member.name = member.name.replace('ssh-config/', '')
                        tar.extract(member, self.ssh_dir)
                        
                        # Definir permissões corretas
                        config_path = self.ssh_dir / member.name
                        config_path.chmod(0o600)
                    
                    print("✓ Configuração SSH restaurada")
                
                # Mostrar manifesto se disponível
                if 'backup_manifest.json' in tar.getnames():
                    manifest_file = tar.extractfile('backup_manifest.json')
                    manifest = json.load(manifest_file)
                    
                    print(f"✓ Backup de {manifest['backup_date'][:10]} restaurado")
                    if manifest['accounts']:
                        print(f"✓ {len(manifest['accounts'])} contas restauradas:")
                        for acc in manifest['accounts']:
                            status = "🟢 ATIVA" if acc['active'] else "⚪ INATIVA"
                            print(f"   - {acc['name']} ({acc['email']}) {status}")
            
            print("✅ Restauração concluída com sucesso!")
            print("💡 Execute 'git-hyper' para verificar as configurações.")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao restaurar backup: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count=5):
        """Remove backups antigos, mantendo apenas os mais recentes"""
        if not self.backup_dir.exists():
            return
        
        backups = sorted(self.backup_dir.glob('git-hyper-backup-*.tar.gz'), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        
        if len(backups) <= keep_count:
            print(f"✓ {len(backups)} backups encontrados (limite: {keep_count})")
            return
        
        old_backups = backups[keep_count:]
        
        print(f"🧹 Removendo {len(old_backups)} backups antigos...")
        for backup in old_backups:
            backup.unlink()
            print(f"   ✓ Removido: {backup.name}")
        
        print(f"✅ Mantidos {keep_count} backups mais recentes.")

def main():
    parser = argparse.ArgumentParser(description='Git Login Manager - Backup e Restauração')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup'],
                       help='Ação a executar')
    parser.add_argument('--name', '-n', help='Nome do backup (para backup)')
    parser.add_argument('--file', '-f', help='Arquivo de backup (para restore)')
    parser.add_argument('--keep', '-k', type=int, default=5, 
                       help='Número de backups a manter (para cleanup)')
    
    args = parser.parse_args()
    
    backup_manager = GitLoginBackup()
    
    if args.action == 'backup':
        backup_manager.create_backup(args.name)
        
    elif args.action == 'list':
        backup_manager.list_backups()
        
    elif args.action == 'restore':
        if not args.file:
            backups = backup_manager.list_backups()
            if backups:
                try:
                    choice = int(input("Digite o número do backup para restaurar (0 para cancelar): "))
                    if 1 <= choice <= len(backups):
                        backup_manager.restore_backup(backups[choice - 1])
                except (ValueError, IndexError):
                    print("❌ Opção inválida.")
            return
        
        backup_manager.restore_backup(args.file)
        
    elif args.action == 'cleanup':
        backup_manager.cleanup_old_backups(args.keep)

if __name__ == '__main__':
    print("🔧 Git Login Manager - Backup e Restauração")
    print("=" * 50)
    main()