#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPS Proxy Manager & Auto Deployer
Công cụ tự động cài đặt, cấu hình và quản lý Proxy trên Linux VPS.
Hỗ trợ:
- Tự động cài đặt 3proxy (HTTP & SOCKS5) với xác thực User/Password.
- Mở cổng Firewall (UFW & Iptables).
- Tab quản lý danh sách VPS.
- Tab quản lý danh sách Proxy & Check Live.
- Xuất danh sách proxy ra định dạng IP:Port:User:Pass.
"""

import sys
import os
import json
import time
import random
import string
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# Thử import paramiko và requests (nếu chưa có sẽ thông báo hướng dẫn cài đặt)
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
    """Sinh chuỗi ngẫu nhiên cho user/password"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


class ProxyManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VPS Proxy Deployer & Manager")
        self.root.geometry("900, 680")
        self.root.minsize(800, 600)

        # Load dữ liệu
        self.data = self.load_data()

        # Tạo giao diện chính
        self.setup_ui()

        # Kiểm tra thư viện phụ thuộc
        self.check_dependencies()

    def check_dependencies(self):
        missing = []
        if paramiko is None:
            missing.append("paramiko")
        if requests is None:
            missing.append("requests")
        if missing:
            msg = f"Thiếu thư viện: {', '.join(missing)}.\n\nVui lòng cài đặt bằng lệnh:\npip install {' '.join(missing)}"
            messagebox.showwarning("Cảnh báo thư viện", msg)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"vps_list": [], "proxy_list": []}

    def save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"Lỗi khi lưu dữ liệu: {e}")

    def setup_ui(self):
        # Notebook (Tabbed container)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Tự động cài đặt Proxy
        self.tab_deploy = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_deploy, text=" ⚡ Cài đặt & Tạo Proxy ")
        self.build_deploy_tab()

        # Tab 2: Quản lý VPS
        self.tab_vps = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_vps, text=" 🖥️ Quản lý VPS ")
        self.build_vps_tab()

        # Tab 3: Quản lý Proxy
        self.tab_proxies = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_proxies, text=" 🌐 Quản lý Proxy ")
        self.build_proxy_tab()

    # =========================================================================
    # TAB 1: CÀI ĐẶT & TẠO PROXY TỰ ĐỘNG
    # =========================================================================
    def build_deploy_tab(self):
        container = ttk.Frame(self.tab_deploy, padding="15")
        container.pack(fill=tk.BOTH, expand=True)

        # Khung thông tin VPS
        vps_group = ttk.LabelFrame(container, text="Thông tin VPS (SSH)", padding="10")
        vps_group.pack(fill=tk.X, pady=(0, 10))

        vps_grid = ttk.Frame(vps_group)
        vps_grid.pack(fill=tk.X)

        # IP
        ttk.Label(vps_grid, text="Địa chỉ IP VPS:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ent_ip = ttk.Entry(vps_grid, width=25)
        self.ent_ip.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Port SSH
        ttk.Label(vps_grid, text="Port SSH:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.ent_ssh_port = ttk.Entry(vps_grid, width=10)
        self.ent_ssh_port.insert(0, "22")
        self.ent_ssh_port.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        # Username
        ttk.Label(vps_grid, text="Username:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ent_user = ttk.Entry(vps_grid, width=25)
        self.ent_user.insert(0, "root")
        self.ent_user.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Password
        ttk.Label(vps_grid, text="Mật khẩu VPS:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.ent_pass = ttk.Entry(vps_grid, width=25, show="*")
        self.ent_pass.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        # Khung cấu hình Proxy
        proxy_group = ttk.LabelFrame(container, text="Cấu hình Proxy mong muốn", padding="10")
        proxy_group.pack(fill=tk.X, pady=(0, 10))

        p_grid = ttk.Frame(proxy_group)
        p_grid.pack(fill=tk.X)

        ttk.Label(p_grid, text="Cổng HTTP Proxy:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ent_proxy_port = ttk.Entry(p_grid, width=15)
        self.ent_proxy_port.insert(0, str(random.randint(10000, 30000)))
        self.ent_proxy_port.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(p_grid, text="Cổng SOCKS5:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.ent_socks_port = ttk.Entry(p_grid, width=15)
        self.ent_socks_port.insert(0, str(int(self.ent_proxy_port.get()) + 1))
        self.ent_socks_port.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(p_grid, text="User Proxy:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ent_proxy_user = ttk.Entry(p_grid, width=20)
        self.ent_proxy_user.insert(0, "user_" + generate_random_string(4))
        self.ent_proxy_user.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(p_grid, text="Pass Proxy:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.ent_proxy_pass = ttk.Entry(p_grid, width=20)
        self.ent_proxy_pass.insert(0, generate_random_string(10))
        self.ent_proxy_pass.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        btn_rand = ttk.Button(p_grid, text="Đổi User/Pass ngẫu nhiên", command=self.randomize_proxy_credentials)
        btn_rand.grid(row=1, column=4, padx=10, pady=5)

        # Nút thực thi
        action_bar = ttk.Frame(container)
        action_bar.pack(fill=tk.X, pady=5)

        self.btn_deploy = ttk.Button(
            action_bar,
            text="🚀 Bắt đầu cài đặt & Khởi tạo Proxy",
            command=self.start_deploy_thread
        )
        self.btn_deploy.pack(side=tk.LEFT, ipady=6, ipadx=15)

        self.lbl_status = ttk.Label(action_bar, text="Sẵn sàng", foreground="gray")
        self.lbl_status.pack(side=tk.LEFT, padx=15)

        # Kết quả xuất ra
        res_frame = ttk.LabelFrame(container, text="Proxy xuất ra (Click để sao chép)", padding="5")
        res_frame.pack(fill=tk.X, pady=5)

        self.ent_result = ttk.Entry(res_frame, font=("Courier", 11, "bold"), foreground="green")
        self.ent_result.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        btn_copy = ttk.Button(res_frame, text="Sao chép", command=self.copy_result_proxy)
        btn_copy.pack(side=tk.RIGHT, padx=5)

        # Nhật ký tiến trình (Log Console)
        log_group = ttk.LabelFrame(container, text="Nhật ký triển khai (Log)", padding="5")
        log_group.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txt_log = scrolledtext.ScrolledText(log_group, height=12, bg="#1e1e1e", fg="#00ff66", font=("Consolas", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def randomize_proxy_credentials(self):
        new_port = random.randint(10000, 35000)
        self.ent_proxy_port.delete(0, tk.END)
        self.ent_proxy_port.insert(0, str(new_port))

        self.ent_socks_port.delete(0, tk.END)
        self.ent_socks_port.insert(0, str(new_port + 1))

        self.ent_proxy_user.delete(0, tk.END)
        self.ent_proxy_user.insert(0, "u_" + generate_random_string(4))

        self.ent_proxy_pass.delete(0, tk.END)
        self.ent_proxy_pass.insert(0, generate_random_string(10))

    def log(self, message):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.txt_log.insert(tk.END, timestamp + message + "\n")
        self.txt_log.see(tk.END)

    def copy_result_proxy(self):
        res = self.ent_result.get().strip()
        if res:
            self.root.clipboard_clear()
            self.root.clipboard_append(res)
            messagebox.showinfo("Thành công", "Đã sao chép định dạng proxy vào bộ nhớ tạm!")

    def start_deploy_thread(self):
        if paramiko is None:
            messagebox.showerror("Lỗi", "Chưa cài đặt thư viện 'paramiko'. Hãy chạy 'pip install paramiko'")
            return

        ip = self.ent_ip.get().strip()
        ssh_port = self.ent_ssh_port.get().strip()
        ssh_user = self.ent_user.get().strip()
        ssh_pass = self.ent_pass.get().strip()

        proxy_port = self.ent_proxy_port.get().strip()
        socks_port = self.ent_socks_port.get().strip()
        proxy_user = self.ent_proxy_user.get().strip()
        proxy_pass = self.ent_proxy_pass.get().strip()

        if not ip or not ssh_pass:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập IP và Mật khẩu của VPS!")
            return

        self.btn_deploy.config(state=tk.DISABLED)
        self.lbl_status.config(text="Đang kết nối và cài đặt...", foreground="orange")
        self.txt_log.delete(1.0, tk.END)

        thread = threading.Thread(
            target=self.run_deployment,
            args=(ip, int(ssh_port), ssh_user, ssh_pass, proxy_port, socks_port, proxy_user, proxy_pass),
            daemon=True
        )
        thread.start()

    def run_deployment(self, ip, ssh_port, ssh_user, ssh_pass, p_port, s_port, p_user, p_pass):
        self.log(f"Đang kết nối SSH tới {ip}:{ssh_port}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(ip, port=ssh_port, username=ssh_user, password=ssh_pass, timeout=15)
            self.log("✅ Kết nối SSH thành công!")

            # Chuẩn bị script cài đặt 3proxy tự động
            self.log("Bắt đầu cài đặt 3proxy và cấu hình tường lửa...")
            setup_commands = f"""
export DEBIAN_FRONTEND=noninteractive
apt-get update -y > /dev/null 2>&1
apt-get install -y 3proxy ufw iptables > /dev/null 2>&1

# Tạo file cấu hình 3proxy
mkdir -p /etc/3proxy
cat << 'EOF' > /etc/3proxy/3proxy.cfg
nserver 8.8.8.8
nserver 1.1.1.1
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
users {p_user}:CL:{p_pass}
auth strong
flush
proxy -p{p_port} -a
socks -p{s_port} -a
EOF

# Phân quyền và khởi động dịch vụ
chmod 600 /etc/3proxy/3proxy.cfg
systemctl restart 3proxy > /dev/null 2>&1 || 3proxy /etc/3proxy/3proxy.cfg &

# Mở cổng Firewall
ufw allow {p_port}/tcp > /dev/null 2>&1 || true
ufw allow {s_port}/tcp > /dev/null 2>&1 || true
iptables -I INPUT -p tcp --dport {p_port} -j ACCEPT > /dev/null 2>&1 || true
iptables -I INPUT -p tcp --dport {s_port} -j ACCEPT > /dev/null 2>&1 || true
"""
            # Chạy lệnh
            stdin, stdout, stderr = ssh.exec_command(setup_commands)
            stdout.channel.recv_exit_status()

            self.log("✅ Cài đặt và cấu hình 3proxy hoàn tất!")

            # Format proxy xuất ra
            proxy_http = f"{ip}:{p_port}:{p_user}:{p_pass}"
            proxy_socks5 = f"{ip}:{s_port}:{p_user}:{p_pass}"

            self.log(f"HTTP Proxy : {proxy_http}")
            self.log(f"SOCKS5     : {proxy_socks5}")

            # Lưu vào danh sách
            self.root.after(0, lambda: self.on_deploy_success(
                ip, ssh_port, ssh_user, ssh_pass, p_port, s_port, p_user, p_pass, proxy_http, proxy_socks5
            ))

        except Exception as e:
            self.log(f"❌ Thất bại: {str(e)}")
            self.root.after(0, lambda: self.on_deploy_failed(str(e)))
        finally:
            ssh.close()

    def on_deploy_success(self, ip, ssh_port, ssh_user, ssh_pass, p_port, s_port, p_user, p_pass, p_http, p_socks):
        self.btn_deploy.config(state=tk.NORMAL)
        self.lbl_status.config(text="Cài đặt thành công!", foreground="green")
        self.ent_result.delete(0, tk.END)
        self.ent_result.insert(0, p_http)

        # Thêm/Cập nhật VPS vào database
        vps_entry = {
            "ip": ip,
            "ssh_port": ssh_port,
            "ssh_user": ssh_user,
            "ssh_pass": ssh_pass,
            "proxy_port": p_port,
            "socks_port": s_port,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        # Kiểm tra trùng IP
        self.data["vps_list"] = [v for v in self.data["vps_list"] if v.get("ip") != ip]
        self.data["vps_list"].append(vps_entry)

        # Thêm Proxy HTTP & SOCKS5
        self.data["proxy_list"].append({
            "ip": ip,
            "port": p_port,
            "type": "HTTP",
            "user": p_user,
            "pass": p_pass,
            "formatted": p_http,
            "status": "Chưa check",
            "vps": ip
        })
        self.data["proxy_list"].append({
            "ip": ip,
            "port": s_port,
            "type": "SOCKS5",
            "user": p_user,
            "pass": p_pass,
            "formatted": p_socks,
            "status": "Chưa check",
            "vps": ip
        })

        self.save_data()
        self.refresh_vps_table()
        self.refresh_proxy_table()
        self.randomize_proxy_credentials()
        messagebox.showinfo("Thành công", f"Đã cấu hình xong Proxy trên VPS {ip}!\n\nProxy HTTP:\n{p_http}")

    def on_deploy_failed(self, error):
        self.btn_deploy.config(state=tk.NORMAL)
        self.lbl_status.config(text="Thất bại", foreground="red")
        messagebox.showerror("Lỗi triển khai", f"Không thể cài đặt proxy trên VPS:\n{error}")

    # =========================================================================
    # TAB 2: QUẢN LÝ VPS
    # =========================================================================
    def build_vps_tab(self):
        container = ttk.Frame(self.tab_vps, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="🔄 Làm mới", command=self.refresh_vps_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📡 Kiểm tra SSH", command=self.check_selected_vps_ssh).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ Xóa VPS khỏi danh sách", command=self.delete_selected_vps).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🛑 Gỡ bỏ 3proxy trên VPS", command=self.uninstall_proxy_on_vps).pack(side=tk.LEFT, padx=5)

        # Bảng hiển thị VPS
        columns = ("ip", "ssh_port", "ssh_user", "proxy_port", "socks_port", "created_at")
        self.tree_vps = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")

        self.tree_vps.heading("ip", text="Địa chỉ IP")
        self.tree_vps.heading("ssh_port", text="Port SSH")
        self.tree_vps.heading("ssh_user", text="User")
        self.tree_vps.heading("proxy_port", text="Port HTTP")
        self.tree_vps.heading("socks_port", text="Port SOCKS5")
        self.tree_vps.heading("created_at", text="Thời gian tạo")

        self.tree_vps.column("ip", width=140, anchor=tk.CENTER)
        self.tree_vps.column("ssh_port", width=80, anchor=tk.CENTER)
        self.tree_vps.column("ssh_user", width=90, anchor=tk.CENTER)
        self.tree_vps.column("proxy_port", width=100, anchor=tk.CENTER)
        self.tree_vps.column("socks_port", width=100, anchor=tk.CENTER)
        self.tree_vps.column("created_at", width=160, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree_vps.yview)
        self.tree_vps.configure(yscrollcommand=scroll_y.set)

        self.tree_vps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_vps_table()

    def refresh_vps_table(self):
        for row in self.tree_vps.get_children():
            self.tree_vps.delete(row)
        for vps in self.data.get("vps_list", []):
            self.tree_vps.insert("", tk.END, values=(
                vps.get("ip", ""),
                vps.get("ssh_port", 22),
                vps.get("ssh_user", "root"),
                vps.get("proxy_port", ""),
                vps.get("socks_port", ""),
                vps.get("created_at", "")
            ))

    def delete_selected_vps(self):
        selected = self.tree_vps.selection()
        if not selected:
            messagebox.showwarning("Chọn VPS", "Vui lòng chọn 1 VPS trong bảng để xóa!")
            return
        item = self.tree_vps.item(selected[0])
        ip = item["values"][0]

        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa VPS {ip} khỏi danh sách?"):
            self.data["vps_list"] = [v for v in self.data["vps_list"] if v.get("ip") != ip]
            self.save_data()
            self.refresh_vps_table()

    def check_selected_vps_ssh(self):
        selected = self.tree_vps.selection()
        if not selected:
            messagebox.showwarning("Chọn VPS", "Vui lòng chọn 1 VPS để kiểm tra kết nối!")
            return
        ip = self.tree_vps.item(selected[0])["values"][0]
        vps = next((v for v in self.data["vps_list"] if v.get("ip") == ip), None)
        if not vps:
            return

        def task():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(vps["ip"], port=int(vps["ssh_port"]), username=vps["ssh_user"], password=vps["ssh_pass"], timeout=8)
                ssh.close()
                messagebox.showinfo("Kết nối SSH", f"✅ VPS {ip} đang hoạt động tốt!")
            except Exception as e:
                messagebox.showerror("Kết nối SSH", f"❌ Không thể kết nối tới {ip}:\n{e}")

        threading.Thread(target=task, daemon=True).start()

    def uninstall_proxy_on_vps(self):
        selected = self.tree_vps.selection()
        if not selected:
            messagebox.showwarning("Chọn VPS", "Vui lòng chọn 1 VPS để gỡ bỏ proxy!")
            return
        ip = self.tree_vps.item(selected[0])["values"][0]
        vps = next((v for v in self.data["vps_list"] if v.get("ip") == ip), None)
        if not vps:
            return

        if not messagebox.askyesno("Xác nhận", f"Bạn muốn tắt và xóa cấu hình 3proxy trên VPS {ip}?"):
            return

        def task():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(vps["ip"], port=int(vps["ssh_port"]), username=vps["ssh_user"], password=vps["ssh_pass"], timeout=10)
                cmd = "systemctl stop 3proxy; pkill 3proxy; rm -rf /etc/3proxy"
                ssh.exec_command(cmd)
                ssh.close()
                messagebox.showinfo("Gỡ bỏ Proxy", f"✅ Đã gỡ bỏ 3proxy trên VPS {ip} thành công!")
            except Exception as e:
                messagebox.showerror("Lỗi gỡ bỏ", f"❌ Không thể gỡ bỏ trên {ip}:\n{e}")

        threading.Thread(target=task, daemon=True).start()

    # =========================================================================
    # TAB 3: QUẢN LÝ PROXY
    # =========================================================================
    def build_proxy_tab(self):
        container = ttk.Frame(self.tab_proxies, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="🔄 Làm mới", command=self.refresh_proxy_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="⚡ Check Live tất cả", command=self.check_all_proxies_live).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📋 Sao chép Proxy đã chọn", command=self.copy_selected_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="💾 Xuất file TXT", command=self.export_proxies_to_txt).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ Xóa Proxy đã chọn", command=self.delete_selected_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🧹 Dọn dẹp Proxy chết", command=self.clean_dead_proxies).pack(side=tk.LEFT, padx=5)

        # Bảng hiển thị Proxy
        columns = ("type", "ip", "port", "user", "pass", "formatted", "status")
        self.tree_proxy = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")

        self.tree_proxy.heading("type", text="Loại")
        self.tree_proxy.heading("ip", text="IP")
        self.tree_proxy.heading("port", text="Cổng")
        self.tree_proxy.heading("user", text="User")
        self.tree_proxy.heading("pass", text="Pass")
        self.tree_proxy.heading("formatted", text="Định dạng IP:Port:User:Pass")
        self.tree_proxy.heading("status", text="Trạng thái Live")

        self.tree_proxy.column("type", width=70, anchor=tk.CENTER)
        self.tree_proxy.column("ip", width=130, anchor=tk.CENTER)
        self.tree_proxy.column("port", width=70, anchor=tk.CENTER)
        self.tree_proxy.column("user", width=100, anchor=tk.W)
        self.tree_proxy.column("pass", width=100, anchor=tk.W)
        self.tree_proxy.column("formatted", width=250, anchor=tk.W)
        self.tree_proxy.column("status", width=110, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree_proxy.yview)
        self.tree_proxy.configure(yscrollcommand=scroll_y.set)

        self.tree_proxy.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_proxy_table()

    def refresh_proxy_table(self):
        for row in self.tree_proxy.get_children():
            self.tree_proxy.delete(row)
        for p in self.data.get("proxy_list", []):
            self.tree_proxy.insert("", tk.END, values=(
                p.get("type", "HTTP"),
                p.get("ip", ""),
                p.get("port", ""),
                p.get("user", ""),
                p.get("pass", ""),
                p.get("formatted", ""),
                p.get("status", "Chưa check")
            ))

    def copy_selected_proxy(self):
        selected = self.tree_proxy.selection()
        if not selected:
            messagebox.showwarning("Chọn Proxy", "Vui lòng chọn proxy muốn sao chép!")
            return
        lines = []
        for s in selected:
            lines.append(self.tree_proxy.item(s)["values"][5])
        clip_text = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(clip_text)
        messagebox.showinfo("Đã chép", f"Đã sao chép {len(lines)} proxy vào clipboard!")

    def export_proxies_to_txt(self):
        proxies = [p.get("formatted", "") for p in self.data.get("proxy_list", []) if p.get("formatted")]
        if not proxies:
            messagebox.showinfo("Trống", "Danh sách proxy hiện đang trống!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Lưu danh sách Proxy"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("\n".join(proxies))
                messagebox.showinfo("Thành công", f"Đã xuất {len(proxies)} proxy ra file:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Lỗi lưu file", str(e))

    def delete_selected_proxy(self):
        selected = self.tree_proxy.selection()
        if not selected:
            messagebox.showwarning("Chọn Proxy", "Vui lòng chọn proxy muốn xóa!")
            return
        formats_to_delete = set()
        for s in selected:
            formats_to_delete.add(self.tree_proxy.item(s)["values"][5])

        self.data["proxy_list"] = [p for p in self.data["proxy_list"] if p.get("formatted") not in formats_to_delete]
        self.save_data()
        self.refresh_proxy_table()

    def clean_dead_proxies(self):
        before = len(self.data["proxy_list"])
        self.data["proxy_list"] = [p for p in self.data["proxy_list"] if p.get("status") != "DIE"]
        after = len(self.data["proxy_list"])
        self.save_data()
        self.refresh_proxy_table()
        messagebox.showinfo("Dọn dẹp", f"Đã xóa {before - after} proxy trạng thái DIE!")

    def check_all_proxies_live(self):
        if requests is None:
            messagebox.showerror("Lỗi", "Chưa cài đặt thư viện 'requests'. Hãy chạy 'pip install requests'")
            return

        proxies = self.data.get("proxy_list", [])
        if not proxies:
            messagebox.showinfo("Trống", "Chưa có proxy nào để kiểm tra!")
            return

        def check_task():
            for p in proxies:
                ptype = p.get("type", "HTTP").lower()
                ip = p.get("ip")
                port = p.get("port")
                user = p.get("user")
                pwd = p.get("pass")

                if ptype == "socks5":
                    proxy_url = f"socks5://{user}:{pwd}@{ip}:{port}"
                else:
                    proxy_url = f"http://{user}:{pwd}@{ip}:{port}"

                try:
                    resp = requests.get(
                        "http://httpbin.org/ip",
                        proxies={"http": proxy_url, "https": proxy_url},
                        timeout=7
                    )
                    if resp.status_code == 200:
                        p["status"] = "LIVE ✅"
                    else:
                        p["status"] = "DIE ❌"
                except Exception:
                    p["status"] = "DIE ❌"

                self.root.after(0, self.refresh_proxy_table)

            self.save_data()
            self.root.after(0, lambda: messagebox.showinfo("Hoàn tất", "Đã kiểm tra xong toàn bộ danh sách proxy!"))

        threading.Thread(target=check_task, daemon=True).start()


def main():
    root = tk.Tk()
    app = ProxyManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
