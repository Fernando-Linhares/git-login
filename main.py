#!/usr/bin/env python3
import os
import sys
import tty
import termios
import subprocess
from pathlib import Path
from app.data_source import DataSource

def get_key():
    """Captura teclas do usuário"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            seq = ch + sys.stdin.read(2)
            return seq
        else:
            return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def colored(text, color_code):
    """Adiciona cores ao texto"""
    return f"\033[{color_code}m{text}\033[0m"

def justify_cell(text, size):
    """Justifica texto em célula de tabela"""
    if len(text) > size:
        return text[:size - 3] + '...'
    else:
        return text.center(size)

def get_input(prompt):
    """Obtém input do usuário (restaura modo normal do terminal)"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return input(prompt)
    finally:
        pass

def print_header():
    """Imprime cabeçalho do programa"""
    print()
    print(colored("  ██████╗  ██████╗ ████████╗", "91") + "  " + colored("██╗      ██████╗  ██████╗ ██╗███╗   ██╗", "96"))
    print(colored(" ██╔════╝    ██╔═╝  ═ ██╔══╝", "91") + "  " + colored("██║     ██╔═══██╗██╔════╝ ██║████╗  ██║", "96"))
    print(colored(" ██║  ███║   ██║      ██║   ", "91") + "  " + colored("██║     ██║   ██║██║  ███╗██║██╔██╗ ██║", "96"))
    print(colored(" ██║   ██║   ██║      ██║   ", "91") + "  " + colored("██║     ██║   ██║██║   ██║██║██║╚██╗██║", "96"))
    print(colored(" ╚██████╔╝ ██████║    ██║   ", "91") + "  " + colored("███████╗╚██████╔╝╚██████╔╝██║██║ ╚████║", "96"))
    print(colored("  ╚═════╝   ╚════╝   ╚═══╝   ", "91") + "  " + colored("╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝", "96"))
    print()

def add_login():
    """Adiciona novo login"""
    os.system('clear')
    print_header()
    print(colored("=== ADICIONAR NOVA CONTA ===", "93"))
    print()
    
    try:
        name = get_input("Nome: ").strip()
        if not name:
            print(colored("Nome não pode estar vazio!", "91"))
            get_input("Pressione Enter para continuar...")
            return
        
        email = get_input("Email: ").strip()
        if not email or '@' not in email:
            print(colored("Email inválido!", "91"))
            get_input("Pressione Enter para continuar...")
            return
        
        print("\nOpções para chave SSH:")
        print("1 - Gerar nova chave SSH")
        print("2 - Usar chave SSH existente")
        
        choice = get_input("Escolha (1 ou 2): ").strip()
        
        datasource = DataSource()
        ssh_key_path = None
        
        if choice == '1':
            print("\nGerando nova chave SSH...")
            ssh_key_path = datasource.generate_ssh_key(name, email)
            if ssh_key_path:
                print(colored(f"Chave SSH gerada: {ssh_key_path}", "92"))
                datasource.set_default(ssh_key_path)
                pub_key = datasource.get_public_key(ssh_key_path)
                if pub_key:
                    print("\n" + colored("CHAVE PÚBLICA (adicione ao GitHub):", "93"))
                    print(colored(pub_key, "96"))
                    print(colored("\nCopie a chave acima e adicione em: GitHub → Settings → SSH Keys", "93"))
            else:
                print(colored("Erro ao gerar chave SSH!", "91"))
                get_input("Pressione Enter para continuar...")
                return
                
        elif choice == '2':
            ssh_key_path = get_input("Caminho para chave SSH privada: ").strip()
            if not Path(ssh_key_path).exists():
                print(colored("Arquivo de chave não encontrado!", "91"))
                get_input("Pressione Enter para continuar...")
                return
        else:
            print(colored("Opção inválida!", "91"))
            get_input("Pressione Enter para continuar...")
            return
        
        # Criar conta
        if datasource.create_account(name, email, ssh_key_path):
            print(colored(f"\nConta '{name}' criada e ativada com sucesso!", "92"))
            print(colored("Configurações Git aplicadas automaticamente.", "92"))
        else:
            print(colored("Erro: Email já cadastrado!", "91"))
        
        datasource.close()
        get_input("Pressione Enter para continuar...")
        
    except KeyboardInterrupt:
        print(colored("\nOperação cancelada!", "93"))
        return
    except Exception as e:
        print(colored(f"Erro: {e}", "91"))
        get_input("Pressione Enter para continuar...")

def list_and_select_account():
    """Lista contas e permite seleção"""
    datasource = DataSource()
    accounts = datasource.list_accounts()
    
    if not accounts:
        print(colored("Nenhuma conta cadastrada!", "93"))
        get_input("Pressione Enter para continuar...")
        datasource.close()
        return
    
    print(colored("=== CONTAS DISPONÍVEIS ===", "93"))
    print()
    print(f"|{justify_cell('ID', 4)}|{justify_cell('NOME', 20)}|{justify_cell('EMAIL', 35)}|{justify_cell('ATIVA', 8)}|")
    print("|" + "-" * 4 + "|" + "-" * 20 + "|" + "-" * 35 + "|" + "-" * 8 + "|")
    
    for id, name, email, ssh_key, active in accounts:
        status = colored("SIM", "92") if active else colored("NÃO", "91")
        print(f"|{justify_cell(str(id), 4)}|{justify_cell(name, 20)}|{justify_cell(email, 35)}|{justify_cell(status, 8)}|")
    
    print()
    try:
        account_id = get_input("ID da conta para ativar (ou Enter para voltar): ").strip()
        if account_id:
            account_id = int(account_id)
            if datasource.activate_account(account_id):
                account = datasource.get_account_by_id(account_id)
                if account:
                    _, name, email, _, _ = account
                    print(colored(f"Conta '{name}' ativada com sucesso!", "92"))
                    print(colored("Configurações Git e SSH aplicadas.", "92"))
            else:
                print(colored("Erro ao ativar conta!", "91"))
            get_input("Pressione Enter para continuar...")
    except (ValueError, KeyboardInterrupt):
        pass
    
    datasource.close()

def show_current_account():
    """Mostra informações da conta atual"""
    datasource = DataSource()
    accounts = datasource.current_account()
    
    print(colored("=== CONTA ATUAL ===", "93"))
    print()
    
    if accounts:
        id, name, email, ssh_key, _ = accounts[0]
        print(f"ID: {colored(str(id), '96')}")
        print(f"Nome: {colored(name, '96')}")
        print(f"Email: {colored(email, '96')}")
        print(f"Chave SSH: {colored(ssh_key, '96')}")
        
        # Mostrar chave pública se disponível
        pub_key = datasource.get_public_key(ssh_key)
        if pub_key:
            print(f"\nChave Pública:")
            print(colored(pub_key, '94'))
    else:
        print(colored("Nenhuma conta ativa!", "93"))
    
    print()
    get_input("Pressione Enter para continuar...")
    datasource.close()

def remove_account():
    """Remove conta"""
    datasource = DataSource()
    accounts = datasource.list_accounts()
    
    if not accounts:
        print(colored("Nenhuma conta cadastrada!", "93"))
        get_input("Pressione Enter para continuar...")
        datasource.close()
        return
    
    print(colored("=== REMOVER CONTA ===", "93"))
    print()
    print(f"|{justify_cell('ID', 4)}|{justify_cell('NOME', 20)}|{justify_cell('EMAIL', 35)}|")
    print("|" + "-" * 4 + "|" + "-" * 20 + "|" + "-" * 35 + "|")
    
    for id, name, email, _, _ in accounts:
        print(f"|{justify_cell(str(id), 4)}|{justify_cell(name, 20)}|{justify_cell(email, 35)}|")
    
    print()
    try:
        account_id = get_input("ID da conta para remover (ou Enter para cancelar): ").strip()
        if account_id:
            account_id = int(account_id)
            account = datasource.get_account_by_id(account_id)
            if account:
                _, name, _, _, _ = account
                confirm = get_input(f"Confirma remoção da conta '{name}'? (s/N): ").strip().lower()
                if confirm == 's':
                    if datasource.delete_account(account_id):
                        print(colored(f"Conta '{name}' removida com sucesso!", "92"))
                    else:
                        print(colored("Erro ao remover conta!", "91"))
            else:
                print(colored("Conta não encontrada!", "91"))
            get_input("Pressione Enter para continuar...")
    except (ValueError, KeyboardInterrupt):
        pass
    
    datasource.close()

def test_git_connection():
    """Testa conexão com GitHub"""
    print(colored("=== TESTANDO CONEXÃO ===", "93"))
    print()
    
    try:
        result = subprocess.run(['ssh', '-T', 'git@github.com'], 
                              capture_output=True, text=True, timeout=10)
        if "successfully authenticated" in result.stderr:
            print(colored("✓ Conexão SSH com GitHub funcionando!", "92"))
        else:
            print(colored("✗ Problema na conexão SSH com GitHub", "91"))
            print(f"Saída: {result.stderr}")
    except subprocess.TimeoutExpired:
        print(colored("✗ Timeout na conexão", "91"))
    except Exception as e:
        print(colored(f"✗ Erro ao testar conexão: {e}", "91"))
    
    print()
    get_input("Pressione Enter para continuar...")

def select_option(option):
    """Processa opção selecionada"""
    if option == 1:  # Adicionar login
        add_login()
    elif option == 2:  # Fazer logon (ativar conta)
        os.system('clear')
        print_header()
        list_and_select_account()
    elif option == 3:  # Listar contas
        os.system('clear')
        print_header()
        list_and_select_account()
    elif option == 4:  # Ver conta atual
        os.system('clear')
        print_header()
        show_current_account()
    elif option == 5:  # Remover conta
        os.system('clear')
        print_header()
        remove_account()
    elif option == 6:  # Testar conexão
        os.system('clear')
        print_header()
        test_git_connection()
    elif option == 7:  # Sair
        return True
    
    return False

def main():
    """Função principal"""
    # Criar diretório se não existir
    git_login_dir = Path.home() / '.git-login'
    if not git_login_dir.exists():
        git_login_dir.mkdir()

    active = 1
    key = 0
    should_exit = False

    while not should_exit:
        os.system('clear')
        print_header()
        
        # Mostrar conta atual
        datasource = DataSource()
        current_accounts = datasource.current_account()
        
        if current_accounts:
            _, name, email, _, _ = current_accounts[0]
            print(colored(f"Conta Ativa: {name} ({email})", "95"))
        else:
            print(colored("Nenhuma conta ativa - Adicione uma nova conta!", "93"))
        
        datasource.close()
        print()

        # Processar entrada do usuário
        if key != 0:
            if key == '\r' or key == '\n':
                should_exit = select_option(active)

            if key == '\x1b[A':  # Seta para cima
                active = 7 if active == 1 else active - 1
            elif key == '\x1b[B':  # Seta para baixo
                active = 1 if active == 7 else active + 1

        # Menu principal
        color = {"actived": "91", "unactived": "96"}
        
        print("Escolha uma opção:")
        print(colored((">>" if active == 1 else "__") + " [1] - Adicionar conta", color["actived"] if active == 1 else color["unactived"]))
        print(colored((">>" if active == 2 else "__") + " [2] - Ativar conta", color["actived"] if active == 2 else color["unactived"]))
        print(colored((">>" if active == 3 else "__") + " [3] - Listar contas", color["actived"] if active == 3 else color["unactived"]))
        print(colored((">>" if active == 4 else "__") + " [4] - Ver conta atual", color["actived"] if active == 4 else color["unactived"]))
        print(colored((">>" if active == 5 else "__") + " [5] - Remover conta", color["actived"] if active == 5 else color["unactived"]))
        print(colored((">>" if active == 6 else "__") + " [6] - Testar conexão", color["actived"] if active == 6 else color["unactived"]))
        print(colored((">>" if active == 7 else "__") + " [q] - Sair", color["actived"] if active == 7 else color["unactived"]))

        # Capturar próxima tecla
        key = get_key()
        
        if key == 'q':
            should_exit = True

    print()
    print(colored("Até logo! 👋", "92"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\n\nPrograma interrompido pelo usuário!", "93"))
        sys.exit(0)