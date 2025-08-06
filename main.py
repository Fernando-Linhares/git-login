#!/usr/bin/env python3
import os
import sys
import tty
import termios
import subprocess
from pathlib import Path
from app.data_source import DataSource

def get_key():
    """Capture user key presses"""
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
    """Add color to text"""
    return f"\033[{color_code}m{text}\033[0m"

def justify_cell(text, size):
    """Justify text in a table cell"""
    if len(text) > size:
        return text[:size - 3] + '...'
    else:
        return text.center(size)

def get_input(prompt):
    """Get user input (restore normal terminal mode)"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return input(prompt)
    finally:
        pass

def print_header():
    """Print program header"""
    print()
    print(colored("  ██████╗ ██╗████████╗", "91") + "  " + colored("██╗  ██╗██╗   ██╗██████╗ ███████╗██████╗ ", "96"))
    print(colored(" ██╔════╝ ██║╚══██╔══╝", "91") + "  " + colored("██║  ██║╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗", "96"))
    print(colored(" ██║  ███╗██║   ██║   ", "91") + "  " + colored("███████║ ╚████╔╝ ██████╔╝█████╗  ██████╔╝", "96"))
    print(colored(" ██║   ██║██║   ██║   ", "91") + "  " + colored("██╔══██║  ╚██╔╝  ██╔═══╝ ██╔══╝  ██╔══██╗", "96"))
    print(colored(" ╚██████╔╝██║   ██║   ", "91") + "  " + colored("██║  ██║   ██║   ██║     ███████╗██║  ██║", "96"))
    print(colored("  ╚═════╝ ╚═╝   ╚═╝   ", "91") + "  " + colored("╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚══════╝╚═╝  ╚═╝", "96"))
    print()

def add_login():
    """Add new login"""
    os.system('clear')
    print_header()
    print(colored("=== ADD NEW ACCOUNT ===", "93"))
    print()
    
    try:
        name = get_input("Name: ").strip()
        if not name:
            print(colored("Name cannot be empty!", "91"))
            get_input("Press Enter to continue...")
            return
        
        email = get_input("Email: ").strip()
        if not email or '@' not in email:
            print(colored("Invalid email!", "91"))
            get_input("Press Enter to continue...")
            return
        
        print("\nSSH Key Options:")
        print("1 - Generate new SSH key")
        print("2 - Use existing SSH key")
        
        choice = get_input("Choose (1 or 2): ").strip()
        
        datasource = DataSource()
        ssh_key_path = None
        
        if choice == '1':
            print("\nGenerating new SSH key...")
            ssh_key_path = datasource.generate_ssh_key(name, email)
            if ssh_key_path:
                print(colored(f"SSH Key generated: {ssh_key_path}", "92"))
                datasource.set_default(ssh_key_path)
                pub_key = datasource.get_public_key(ssh_key_path)
                if pub_key:
                    print("\n" + colored("PUBLIC KEY (add to GitHub):", "93"))
                    print(colored(pub_key, "96"))
                    print(colored("\nCopy the key above and add to: GitHub → Settings → SSH Keys", "93"))
            else:
                print(colored("Error generating SSH key!", "91"))
                get_input("Press Enter to continue...")
                return
                
        elif choice == '2':
            ssh_key_path = get_input("Path to private SSH key: ").strip()
            if not Path(ssh_key_path).exists():
                print(colored("Key file not found!", "91"))
                get_input("Press Enter to continue...")
                return
        else:
            print(colored("Invalid option!", "91"))
            get_input("Press Enter to continue...")
            return
        
        if datasource.create_account(name, email, ssh_key_path):
            print(colored(f"\nAccount '{name}' created and activated successfully!", "92"))
            print(colored("Git settings applied automatically.", "92"))
        else:
            print(colored("Error: Email already registered!", "91"))
        
        datasource.close()
        get_input("Press Enter to continue...")
        
    except KeyboardInterrupt:
        print(colored("\nOperation cancelled!", "93"))
        return
    except Exception as e:
        print(colored(f"Error: {e}", "91"))
        get_input("Press Enter to continue...")

def list_and_select_account():
    """List accounts and allow selection"""
    datasource = DataSource()
    accounts = datasource.list_accounts()
    
    if not accounts:
        print(colored("No accounts registered!", "93"))
        get_input("Press Enter to continue...")
        datasource.close()
        return
    
    print(colored("=== AVAILABLE ACCOUNTS ===", "93"))
    print()
    print(f"|{justify_cell('ID', 4)}|{justify_cell('NAME', 20)}|{justify_cell('EMAIL', 35)}|{justify_cell('ACTIVE', 8)}|")
    print("|" + "-" * 4 + "|" + "-" * 20 + "|" + "-" * 35 + "|" + "-" * 8 + "|")
    
    for id, name, email, ssh_key, active in accounts:
        status = "YES" if active else "NO"
        print(f"|{justify_cell(str(id), 4)}|{justify_cell(name, 20)}|{justify_cell(email, 35)}|{justify_cell(status, 8)}|")
    
    print()
    try:
        account_id = get_input("Account ID to activate (or Enter to go back): ").strip()
        if account_id:
            account_id = int(account_id)
            if datasource.activate_account(account_id):
                account = datasource.get_account_by_id(account_id)
                if account:
                    _, name, email, _, _ = account
                    print(colored(f"Account '{name}' activated successfully!", "92"))
                    print(colored("Git and SSH settings applied.", "92"))
            else:
                print(colored("Error activating account!", "91"))
            get_input("Press Enter to continue...")
    except (ValueError, KeyboardInterrupt):
        pass
    
    datasource.close()

def show_current_account():
    """Show current account information"""
    datasource = DataSource()
    accounts = datasource.current_account()
    
    print(colored("=== CURRENT ACCOUNT ===", "93"))
    print()
    
    if accounts:
        id, name, email, ssh_key, _ = accounts[0]
        print(f"ID: {colored(str(id), '96')}")
        print(f"Name: {colored(name, '96')}")
        print(f"Email: {colored(email, '96')}")
        print(f"SSH Key: {colored(ssh_key, '96')}")
        
        pub_key = datasource.get_public_key(ssh_key)
        if pub_key:
            print(f"\nPublic Key:")
            print(colored(pub_key, '94'))
    else:
        print(colored("No active account!", "93"))
    
    print()
    get_input("Press Enter to continue...")
    datasource.close()

def remove_account():
    """Remove account"""
    datasource = DataSource()
    accounts = datasource.list_accounts()
    
    if not accounts:
        print(colored("No accounts registered!", "93"))
        get_input("Press Enter to continue...")
        datasource.close()
        return
    
    print(colored("=== REMOVE ACCOUNT ===", "93"))
    print()
    print(f"|{justify_cell('ID', 4)}|{justify_cell('NAME', 20)}|{justify_cell('EMAIL', 35)}|")
    print("|" + "-" * 4 + "|" + "-" * 20 + "|" + "-" * 35 + "|")
    
    for id, name, email, _, _ in accounts:
        print(f"|{justify_cell(str(id), 4)}|{justify_cell(name, 20)}|{justify_cell(email, 35)}|")
    
    print()
    try:
        account_id = get_input("Account ID to remove (or Enter to cancel): ").strip()
        if account_id:
            account_id = int(account_id)
            account = datasource.get_account_by_id(account_id)
            if account:
                _, name, _, _, _ = account
                confirm = get_input(f"Confirm removal of account '{name}'? (y/N): ").strip().lower()
                if confirm == 'y':
                    if datasource.delete_account(account_id):
                        print(colored(f"Account '{name}' removed successfully!", "92"))
                    else:
                        print(colored("Error removing account!", "91"))
            else:
                print(colored("Account not found!", "91"))
            get_input("Press Enter to continue...")
    except (ValueError, KeyboardInterrupt):
        pass
    
    datasource.close()

def test_git_connection():
    """Test GitHub connection"""
    print(colored("=== TESTING CONNECTION ===", "93"))
    print()
    
    try:
        result = subprocess.run(['ssh', '-T', 'git@github.com'], 
                              capture_output=True, text=True, timeout=10)
        if "successfully authenticated" in result.stderr:
            print(colored("✓ SSH connection to GitHub working!", "92"))
        else:
            print(colored("✗ SSH connection to GitHub failed", "91"))
            print(f"Output: {result.stderr}")
    except subprocess.TimeoutExpired:
        print(colored("✗ Connection timeout", "91"))
    except Exception as e:
        print(colored(f"✗ Error testing connection: {e}", "91"))
    
    print()
    get_input("Press Enter to continue...")

def select_option(option):
    """Process selected option"""
    if option == 1:
        add_login()
    elif option == 2:
        os.system('clear')
        print_header()
        list_and_select_account()
    elif option == 3:
        os.system('clear')
        print_header()
        list_and_select_account()
    elif option == 4:
        os.system('clear')
        print_header()
        show_current_account()
    elif option == 5:
        os.system('clear')
        print_header()
        remove_account()
    elif option == 6:
        os.system('clear')
        print_header()
        test_git_connection()
    elif option == 7:
        return True
    
    return False

def main():
    """Main function"""
    git_login_dir = Path.home() / '.git-login'
    if not git_login_dir.exists():
        git_login_dir.mkdir()

    active = 1
    key = 0
    should_exit = False

    while not should_exit:
        os.system('clear')
        print_header()
        
        datasource = DataSource()
        current_accounts = datasource.current_account()
        
        if current_accounts:
            _, name, email, _, _ = current_accounts[0]
            print(colored(f"Active Account: {name} ({email})", "95"))
        else:
            print(colored("No active account - Add a new one!", "93"))
        
        datasource.close()
        print()

        if key != 0:
            if key == '\r' or key == '\n':
                should_exit = select_option(active)

            if key == '\x1b[A':  # Up arrow
                active = 7 if active == 1 else active - 1
            elif key == '\x1b[B':  # Down arrow
                active = 1 if active == 7 else active + 1

        color = {"actived": "91", "unactived": "96"}
        
        print("Choose an option:")
        print(colored((">>" if active == 1 else "__") + " [1] - Add account", color["actived"] if active == 1 else color["unactived"]))
        print(colored((">>" if active == 2 else "__") + " [2] - Activate account", color["actived"] if active == 2 else color["unactived"]))
        print(colored((">>" if active == 3 else "__") + " [3] - List accounts", color["actived"] if active == 3 else color["unactived"]))
        print(colored((">>" if active == 4 else "__") + " [4] - View current account", color["actived"] if active == 4 else color["unactived"]))
        print(colored((">>" if active == 5 else "__") + " [5] - Remove account", color["actived"] if active == 5 else color["unactived"]))
        print(colored((">>" if active == 6 else "__") + " [6] - Test connection", color["actived"] if active == 6 else color["unactived"]))
        print(colored((">>" if active == 7 else "__") + " [q] - Quit", color["actived"] if active == 7 else color["unactived"]))

        key = get_key()
        
        if key == 'q':
            should_exit = True

    print()
    print(colored("See you later! 👋", "92"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\n\nProgram interrupted by user!", "93"))
        sys.exit(0)
