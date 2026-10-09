#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPS Proxy Manager - CLI Version (Dành cho Terminal / Điện thoại)
"""

import sys
import os
import json
import time
import random
import string

try:
    import paramiko
except ImportError:
    paramiko = None

try:
    import requests
except ImportError:
    requests = None

DATA_FILE = "vps_proxies_data.json"

def generate_random_string(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"vps_list": [], "proxy_list": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

def deploy_proxy(data):
    if paramiko is None:
        print("[-] Lỗi: Chưa cài paramiko. Chạy: apk add py3-paramiko")
        return

    print("\n--- [1] KHỞI TẠO PROXY TRÊN VPS ---")
    ip = input("Nhập IP VPS: ").strip()
    if not ip:
        print("[-] IP không được để trống!")
        return

    ssh_port_in = input("Port SSH [mặc định 22]: ").strip()
    ssh_port = int(ssh_port_in) if ssh_port_in else 22
    ssh_user = input("Username SSH [mặc định root]: ").strip() or "root"
    ssh_pass = input("Mật khẩu VPS: ").strip()

    proxy_port = random.randint(10000, 30000)
    socks_port = proxy_port + 1
    proxy_user = "u_" + generate_random_string(4)
    proxy_pass = generate_random_string(10)

    print(f"\n[+] Đang kết nối SSH tới {ip}:{ssh_port}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ip, port=ssh_port, username=ssh_user, password=ssh_pass, timeout=15)
        print("[+] Kết nối SSH thành công! Đang cài đặt 3proxy...")

        setup_commands = f"""
export DEBIAN_FRONTEND=noninteractive
apt-get update -y > /dev/null 2>&1
apt-get install -y 3proxy ufw iptables > /dev/null 2>&1
mkdir -p /etc/3proxy
cat << 'EOF' > /etc/3proxy/3proxy.cfg
nserver 8.8.8.8
nserver 1.1.1.1
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
users {proxy_user}:CL:{proxy_pass}
auth strong
flush
proxy -p{proxy_port} -a
socks -p{socks_port} -a
EOF
chmod 600 /etc/3proxy/3proxy.cfg
systemctl restart 3proxy > /dev/null 2>&1 || 3proxy /etc/3proxy/3proxy.cfg &
ufw allow {proxy_port}/tcp > /dev/null 2>&1 || true
ufw allow {socks_port}/tcp > /dev/null 2>&1 || true
iptables -I INPUT -p tcp --dport {proxy_port} -j ACCEPT > /dev/null 2>&1 || true
iptables -I INPUT -p tcp --dport {socks_port} -j ACCEPT > /dev/null 2>&1 || true
"""
        stdin, stdout, stderr = ssh.exec_command(setup_commands)
        stdout.channel.recv_exit_status()

        http_proxy = f"{ip}:{proxy_port}:{proxy_user}:{proxy_pass}"
        socks_proxy = f"{ip}:{socks_port}:{proxy_user}:{proxy_pass}"

        print("\n==========================================")
        print("✅ CÀI ĐẶT THÀNH CÔNG!")
        print(f"HTTP Proxy : {http_proxy}")
        print(f"SOCKS5     : {socks_proxy}")
        print("==========================================\n")

        # Lưu dữ liệu
        data["vps_list"] = [v for v in data["vps_list"] if v.get("ip") != ip]
        data["vps_list"].append({
            "ip": ip, "ssh_port": ssh_port, "ssh_user": ssh_user, "ssh_pass": ssh_pass,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        data["proxy_list"].append({
            "type": "HTTP", "formatted": http_proxy, "status": "Chưa check"
        })
        data["proxy_list"].append({
            "type": "SOCKS5", "formatted": socks_proxy, "status": "Chưa check"
        })
        save_data(data)

    except Exception as e:
        print(f"[-] Thất bại: {e}")
    finally:
        ssh.close()

def list_proxies(data):
    proxies = data.get("proxy_list", [])
    print(f"\n--- DANH SÁCH PROXY ({len(proxies)}) ---")
    if not proxies:
        print("Chưa có proxy nào.")
        return
    for idx, p in enumerate(proxies, 1):
        print(f"{idx}. [{p.get('type')}] {p.get('formatted')} - Trạng thái: {p.get('status')}")

def list_vps(data):
    vps_list = data.get("vps_list", [])
    print(f"\n--- DANH SÁCH VPS ĐÃ LƯU ({len(vps_list)}) ---")
    if not vps_list:
        print("Chưa có VPS nào.")
        return
    for idx, v in enumerate(vps_list, 1):
        print(f"{idx}. IP: {v.get('ip')} | User: {v.get('ssh_user')} | Ngày tạo: {v.get('created_at')}")

def main():
    data = load_data()
    while True:
        print("\n=== MENU QUẢN LÝ PROXY VPS ===")
        print("1. Khởi tạo Proxy mới trên VPS")
        print("2. Xem danh sách Proxy đã tạo")
        print("3. Xem danh sách VPS")
        print("4. Xuất danh sách Proxy ra file proxies.txt")
        print("0. Thoát")
        choice = input("Chọn chức năng (0-4): ").strip()

        if choice == "1":
            deploy_proxy(data)
        elif choice == "2":
            list_proxies(data)
        elif choice == "3":
            list_vps(data)
        elif choice == "4":
            proxies = [p.get("formatted", "") for p in data.get("proxy_list", []) if p.get("formatted")]
            if proxies:
                with open("proxies.txt", "w", encoding="utf-8") as f:
                    f.write("\n".join(proxies))
                print(f"[+] Đã xuất {len(proxies)} proxy ra file proxies.txt!")
            else:
                print("[-] Không có proxy để xuất.")
        elif choice == "0":
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
