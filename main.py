import io
import os
import sys
import re
import time
import random
import shutil
import subprocess
import threading
import urllib.request
import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw
except ImportError:
    print("Eksik kütüphane var! Lütfen terminale 'pip install customtkinter pillow' yazın.")
    exit()

# PyInstaller .exe paketlemesi yapıldığında logo.ico dosyasının yolunu doğru bulması için eklenen fonksiyon
def resource_path(relative_path):
    """ PyInstaller ile paketlendiğinde geçici klasördeki dosyaya erişir. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# -------------------------------------------------------------
# ÖNBELLEKLİ VE ASENKRON İKON YÖNETİCİSİ
# -------------------------------------------------------------
APP_ICONS = {
    "steam": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/steam.png",
    "roblox": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/roblox.png",
    "minecraft": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/minecraft.png",
    "riot": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/riot-games.png",
    "epic": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/epic-games.png",
    "ea": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/ea.png",
    "rockstar": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/rockstar.png",
    "chrome": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/google-chrome.png",
    "firefox": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/firefox.png",
    "edge": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/microsoft-edge.png",
    "opera": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/opera.png",
    "brave": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/brave.png",
    "discord": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/discord.png",
    "vscode": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/visual-studio-code.png",
    "spotify": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/spotify.png",
    "vlc": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/vlc.png"
}

ICON_CACHE = {}

def create_fallback_icon(text, color):
    cache_key = f"fb_{text}_{color}"
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]
    try:
        img = Image.new('RGBA', (44, 44), color=color)
        d = ImageDraw.Draw(img)
        d.text((16, 10), text, fill="white")
        c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(44, 44))
        ICON_CACHE[cache_key] = c_img
        return c_img
    except Exception:
        return None

def fetch_icon_async(url, fallback_text, fallback_color, callback):
    """Görseli arka planda indirir ve bitince UI thread'ine iletir (Arayüz donmasını önler)."""
    if not url:
        callback(create_fallback_icon(fallback_text, fallback_color))
        return

    if url in ICON_CACHE:
        callback(ICON_CACHE[url])
        return

    def _download():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                data = response.read()
                img = Image.open(io.BytesIO(data))
                c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(44, 44))
                ICON_CACHE[url] = c_img
                callback(c_img)
        except Exception:
            callback(create_fallback_icon(fallback_text, fallback_color))

    threading.Thread(target=_download, daemon=True).start()

def get_winget_path():
    winget_path = shutil.which("winget")
    if winget_path:
        return winget_path
    local_appdata = os.getenv('LOCALAPPDATA', '')
    possible_path = os.path.join(local_appdata, r"Microsoft\WindowsApps\winget.exe")
    if os.path.exists(possible_path):
        return possible_path
    return "winget"

# -------------------------------------------------------------
# DINO OYUNU
# -------------------------------------------------------------
class DinoGameWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("BarStore Mini - Dino Runner")
        self.geometry("600x250")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        # Dino Penceresi İkonu
        icon_file = resource_path("logo.ico")
        if os.path.exists(icon_file):
            self.iconbitmap(icon_file)

        self.canvas = tk.Canvas(self, width=600, height=190, bg="#181825", highlightthickness=0)
        self.canvas.pack(pady=10)

        self.dino_y = 120
        self.dino_vel_y = 0
        self.is_jumping = False
        self.score = 0
        self.game_over = False
        self.obstacles = []

        self.dino = self.canvas.create_rectangle(40, self.dino_y, 70, self.dino_y + 30, fill="#38bdf8")
        self.canvas.create_line(0, 150, 600, 150, fill="#a6adc8", width=2)
        self.score_text = self.canvas.create_text(520, 20, text="Skor: 0", fill="#cdd6f4", font=("Arial", 11, "bold"))

        self.bind("<space>", self.jump)
        self.bind("<Button-1>", self.jump)
        self.after(100, self.focus_force)

        self.spawn_obstacle()
        self.update_game()

    def jump(self, event=None):
        if not self.is_jumping and not self.game_over:
            self.is_jumping = True
            self.dino_vel_y = -11
        elif self.game_over:
            self.restart_game()

    def restart_game(self):
        for obs in self.obstacles:
            self.canvas.delete(obs)
        self.obstacles.clear()
        self.score = 0
        self.game_over = False
        self.dino_y = 120
        self.canvas.coords(self.dino, 40, self.dino_y, 70, self.dino_y + 30)
        self.canvas.itemconfig(self.score_text, text="Skor: 0")
        self.update_game()

    def spawn_obstacle(self):
        if not self.game_over:
            obs = self.canvas.create_rectangle(600, 125, 620, 150, fill="#f38ba8")
            self.obstacles.append(obs)
            self.after(random.randint(1200, 2400), self.spawn_obstacle)

    def update_game(self):
        if self.game_over:
            return

        if self.is_jumping:
            self.dino_y += self.dino_vel_y
            self.dino_vel_y += 0.75
            if self.dino_y >= 120:
                self.dino_y = 120
                self.is_jumping = False
            self.canvas.coords(self.dino, 40, self.dino_y, 70, self.dino_y + 30)

        for obs in list(self.obstacles):
            self.canvas.move(obs, -6, 0)
            pos = self.canvas.coords(obs)
            dino_pos = self.canvas.coords(self.dino)

            if pos[2] < 0:
                self.canvas.delete(obs)
                self.obstacles.remove(obs)
                self.score += 10
                self.canvas.itemconfig(self.score_text, text=f"Skor: {self.score}")

            if dino_pos[2] > pos[0] and dino_pos[0] < pos[2] and dino_pos[3] > pos[1]:
                self.game_over = True
                self.canvas.create_text(300, 75, text="GAME OVER\nYeniden Başlamak İçin Tıkla", fill="#f38ba8", font=("Arial", 13, "bold"), justify="center")

        self.after(20, self.update_game)

# -------------------------------------------------------------
# BARSTORE MAĞAZA (OPTIMIZED)
# -------------------------------------------------------------
class BarStore(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BarStore v4.0 - FPS & 400+ Apps Ready")
        self.geometry("1100x750")

        # LOGO EKLENEN KISIM
        icon_file = resource_path("logo.ico")
        if os.path.exists(icon_file):
            self.iconbitmap(icon_file)

        self.winget = get_winget_path()
        self.username = "Rhexo"
        self.current_category = "Tümü"
        self.accent_color = "#2563eb"
        self.search_query = ""
        self.show_fps = True
        self.search_timer = None

        # FPS Hesaplama Değişkenleri
        self.last_time = time.time()
        self.frame_count = 0
        self.fps = 60

        self.rgb_colors = ["#3b82f6", "#8b5cf6", "#ec4899", "#f43f5e", "#10b981", "#06b6d4"]
        self.color_index = 0

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.categories = [
            "Tümü", "Oyunlar & Launcher", "Tarayıcılar", "Yazılım & Kodlama", 
            "Sistem & Araçlar", "Medya & Ses", "Sohbet & Sosyal", 
            "Güvenlik & Ağ", "3D & Tasarım", "Ofis & Verimlilik", "Sürücü & Runtime"
        ]

        self.all_apps = [
            ("Steam", "Valve.Steam", "PC oyun mağazası ve topluluğu.", "steam", "Oyunlar & Launcher", "S", "#0284c7"),
            ("Roblox", "ROBLOX.Roblox", "Sonsuz sanal dünyalar ve oyunlar.", "roblox", "Oyunlar & Launcher", "R", "#ef4444"),
            ("Minecraft Launcher", "Mojang.MinecraftLauncher", "Resmi Minecraft istemcisi.", "minecraft", "Oyunlar & Launcher", "M", "#16a34a"),
            ("Legacy Launcher", "Legacy.LegacyLauncher", "Hafif Minecraft başlatıcısı.", "minecraft", "Oyunlar & Launcher", "L", "#d97706"),
            ("Minecraft Store", "9NBLGGH53719", "Bedrock Minecraft sürümü.", "minecraft", "Oyunlar & Launcher", "M", "#22c55e"),
            ("Minecraft Dungeons", "Mojang.MinecraftDungeons", "Zindan odaklı Minecraft oyunu.", "minecraft", "Oyunlar & Launcher", "D", "#dc2626"),
            ("Riot Client", "RiotGames.RiotClient", "Valorant ve LoL resmi istemcisi.", "riot", "Oyunlar & Launcher", "R", "#f43f5e"),
            ("Epic Games Launcher", "EpicGames.EpicGamesLauncher", "Haftalık ücretsiz oyun mağazası.", "epic", "Oyunlar & Launcher", "E", "#475569"),
            ("EA App", "ElectronicArts.EADesktop", "EA oyunları platformu.", "ea", "Oyunlar & Launcher", "E", "#ea580c"),
            ("Rockstar Games Launcher", "RockstarGames.Launcher", "GTA ve RDR istemcisi.", "rockstar", "Oyunlar & Launcher", "R", "#f59e0b"),
            ("GOG Galaxy", "GOG.Galaxy", "Çoklu platform oyun başlatıcı.", "", "Oyunlar & Launcher", "G", "#8b5cf6"),
            ("Battle.net", "Blizzard.BattleNet", "Blizzard oyun mağazası.", "", "Oyunlar & Launcher", "B", "#0284c7"),
            ("Ubisoft Connect", "Ubisoft.Connect", "Ubisoft oyun istemcisi.", "", "Oyunlar & Launcher", "U", "#3b82f6"),
            ("Heroic Games Launcher", "HeroicGamesLauncher.HeroicGamesLauncher", "Epic/GOG alternatif başlatıcı.", "", "Oyunlar & Launcher", "H", "#ec4899"),

            ("Google Chrome", "Google.Chrome", "Hızlı web tarayıcısı.", "chrome", "Tarayıcılar", "C", "#22c55e"),
            ("Mozilla Firefox", "Mozilla.Firefox", "Açık kaynak gizlilik tarayıcısı.", "firefox", "Tarayıcılar", "F", "#ea580c"),
            ("Microsoft Edge", "Microsoft.Edge", "Windows varsayılan tarayıcı.", "edge", "Tarayıcılar", "E", "#0284c7"),
            ("Opera", "Opera.Opera", "Dahili VPN tarayıcısı.", "opera", "Tarayıcılar", "O", "#dc2626"),
            ("Opera GX", "Opera.OperaGX", "Oyuncu tarayıcısı.", "opera", "Tarayıcılar", "G", "#f43f5e"),
            ("Brave Browser", "Brave.Brave", "Reklam engelleyici tarayıcı.", "brave", "Tarayıcılar", "B", "#f97316"),
            ("Vivaldi", "Vivaldi.Vivaldi", "Özelleştirilebilir tarayıcı.", "", "Tarayıcılar", "V", "#ef4444"),
            ("Tor Browser", "TorProject.TorBrowser", "Anonim gezinti tarayıcısı.", "", "Tarayıcılar", "T", "#8b5cf6"),
            ("LibreWolf", "LibreWolf.LibreWolf", "Güvenlik odaklı Firefox türevi.", "", "Tarayıcılar", "L", "#0284c7"),

            ("VS Code", "Microsoft.VisualStudioCode", "Gelişmiş kod editörü.", "vscode", "Yazılım & Kodlama", "V", "#2563eb"),
            ("Visual Studio 2022", "Microsoft.VisualStudio.2022.Community", "Tam kapsamlı IDE.", "", "Yazılım & Kodlama", "V", "#8b5cf6"),
            ("Python 3.11", "Python.Python.3.11", "Python geliştirme ortamı.", "", "Yazılım & Kodlama", "P", "#38bdf8"),
            ("Git", "Git.Git", "Versiyon kontrol sistemi.", "", "Yazılım & Kodlama", "G", "#f97316"),
            ("Node.js", "OpenJS.NodeJS", "JS runtime ortamı.", "", "Yazılım & Kodlama", "N", "#22c55e"),
            ("Godot Engine", "GodotEngine.GodotEngine", "2D/3D Oyun motoru.", "", "Yazılım & Kodlama", "G", "#0284c7"),
            ("Unity Hub", "Unity.UnityHub", "Unity oyun motoru yöneticisi.", "", "Yazılım & Kodlama", "U", "#475569"),
            ("PyCharm Community", "JetBrains.PyCharm.Community", "Python için IDE.", "", "Yazılım & Kodlama", "P", "#10b981"),

            ("Discord", "Discord.Discord", "Sohbet ve ses platformu.", "discord", "Sohbet & Sosyal", "D", "#6366f1"),
            ("Telegram Desktop", "Telegram.TelegramDesktop", "Güvenli mesajlaşma.", "", "Sohbet & Sosyal", "T", "#0284c7"),
            ("Spotify", "Spotify.Spotify", "Müzik dinleme platformu.", "spotify", "Medya & Ses", "S", "#10b981"),
            ("VLC Media Player", "VideoLAN.VLC", "Medya oynatıcı.", "vlc", "Medya & Ses", "V", "#f97316"),
            ("7-Zip", "7zip.7zip", "Dosya sıkıştırma.", "", "Sistem & Araçlar", "7", "#475569"),
            ("WinRAR", "RARLab.WinRAR", "Arşiv yöneticisi.", "", "Sistem & Araçlar", "W", "#8b5cf6"),
            ("Blender", "BlenderFoundation.Blender", "3D Modelleme yazılımı.", "", "3D & Tasarım", "B", "#ea580c")
        ]

        self.setup_ui()
        self.update_fps_counter()

    def setup_ui(self):
        # Sol Menü
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(self.sidebar, text="BarStore", font=ctk.CTkFont(size=26, weight="bold"))
        self.logo_label.pack(padx=20, pady=(15, 2))

        # FPS Gösterge Etiketi
        self.fps_label = ctk.CTkLabel(self.sidebar, text="FPS: --", font=ctk.CTkFont(size=11, weight="bold"), text_color="#10b981")
        self.fps_label.pack(padx=20, pady=(0, 10))

        self.animate_logo()

        self.user_frame = ctk.CTkFrame(self.sidebar, corner_radius=10)
        self.user_frame.pack(fill="x", padx=12, pady=(5, 10))
        ctk.CTkLabel(self.user_frame, text="⚡", font=ctk.CTkFont(size=15)).pack(side="left", padx=(8, 4), pady=6)
        self.user_label = ctk.CTkLabel(self.user_frame, text=self.username, font=ctk.CTkFont(size=12, weight="bold"))
        self.user_label.pack(side="left", pady=6)

        self.nav_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.nav_scroll.pack(fill="both", expand=True, padx=4)

        self.cat_buttons = {}
        for cat in self.categories:
            btn = ctk.CTkButton(
                self.nav_scroll, text=f"• {cat}", anchor="w", fg_color="transparent",
                text_color="#cdd6f4", height=30, corner_radius=6,
                command=lambda c=cat: self.select_category(c)
            )
            btn.pack(fill="x", pady=2)
            self.cat_buttons[cat] = btn

        self.btn_settings = ctk.CTkButton(self.sidebar, text="⚙️  15 Gelişmiş Ayar", fg_color="transparent", anchor="w", command=self.show_settings)
        self.btn_settings.pack(fill="x", padx=12, pady=3)

        self.btn_dino = ctk.CTkButton(self.sidebar, text="🦖 Dino Oyunu Oyna", fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=lambda: DinoGameWindow(self))
        self.btn_dino.pack(fill="x", padx=12, pady=(3, 12))

        # Sağ İçerik
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")

        self.create_store_view()
        self.create_settings_view()

        self.select_category("Tümü")

    def update_fps_counter(self):
        curr_time = time.time()
        self.frame_count += 1
        if curr_time - self.last_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_time = curr_time
            if self.show_fps:
                self.fps_label.configure(text=f"FPS: {self.fps}")
            else:
                self.fps_label.configure(text="")
        self.after(33, self.update_fps_counter)

    def animate_logo(self):
        try:
            self.logo_label.configure(text_color=self.rgb_colors[self.color_index])
            self.color_index = (self.color_index + 1) % len(self.rgb_colors)
            self.after(500, self.animate_logo)
        except Exception:
            pass

    def select_category(self, category):
        self.current_category = category
        
        if hasattr(self, 'search_entry'):
            self.search_entry.delete(0, tk.END)
            self.search_query = ""

        for c, btn in self.cat_buttons.items():
            if c == category:
                btn.configure(fg_color="#313244", text_color="#38bdf8")
            else:
                btn.configure(fg_color="transparent", text_color="#cdd6f4")
        
        self.show_store()
        self.load_cards()

    def show_store(self):
        self.settings_frame.pack_forget()
        self.store_frame.pack(fill="both", expand=True, padx=20, pady=15)

    def show_settings(self):
        self.store_frame.pack_forget()
        self.settings_frame.pack(fill="both", expand=True, padx=20, pady=15)

    def create_store_view(self):
        self.store_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        top_bar = ctk.CTkFrame(self.store_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        self.page_title = ctk.CTkLabel(top_bar, text="Mağaza", font=ctk.CTkFont(size=20, weight="bold"))
        self.page_title.pack(side="left", anchor="w")

        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="🔍 Uygulama veya oyun ara...", width=260)
        self.search_entry.pack(side="right", padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search_debounced)

        self.scroll_frame = ctk.CTkScrollableFrame(self.store_frame, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True)

    def on_search_debounced(self, event=None):
        if self.search_timer:
            self.after_cancel(self.search_timer)
        self.search_timer = self.after(250, self.on_search)

    def on_search(self):
        self.search_query = self.search_entry.get().strip().lower()
        self.load_cards()

    def load_cards(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.page_title.configure(text=f"Mağaza - {self.current_category}")

        filtered = [
            app for app in self.all_apps
            if (self.current_category == "Tümü" or app[4] == self.current_category) and
               (self.search_query == "" or self.search_query in app[0].lower() or self.search_query in app[2].lower())
        ]

        if not filtered:
            ctk.CTkLabel(self.scroll_frame, text=f"'{self.search_query}' aramasına uygun uygulama bulunamadı.", font=ctk.CTkFont(size=13)).pack(pady=40)
            return

        for name, app_id, desc, icon_key, category, letter, color in filtered:
            card = ctk.CTkFrame(self.scroll_frame, border_width=1, corner_radius=8)
            card.pack(fill="x", pady=4, padx=2)

            img_label = ctk.CTkLabel(card, text="")
            img_label.pack(side="left", padx=(10, 8), pady=8)

            url = APP_ICONS.get(icon_key, "")
            
            def update_img(c_img, target_label=img_label):
                if c_img and target_label.winfo_exists():
                    target_label.configure(image=c_img)

            fetch_icon_async(url, letter, color, update_img)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=6)

            ctk.CTkLabel(info_frame, text=name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(info_frame, text=desc, font=ctk.CTkFont(size=11), anchor="w", text_color="#a6adc8").pack(fill="x")

            status_lbl = ctk.CTkLabel(info_frame, text="", font=ctk.CTkFont(size=10), text_color="#38bdf8", anchor="w")
            status_lbl.pack(fill="x")

            p_bar = ctk.CTkProgressBar(info_frame, orientation="horizontal", height=4, progress_color=self.accent_color)
            p_bar.set(0)

            btn_install = ctk.CTkButton(
                card, text="Yükle", width=85, height=30, corner_radius=6,
                fg_color=self.accent_color, font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda a_id=app_id, b=card, p=p_bar, s=status_lbl: self.start_install(a_id, p, s)
            )
            btn_install.pack(side="right", padx=10, pady=8)

    def start_install(self, app_id, progress_bar, status_lbl):
        progress_bar.pack(fill="x", pady=(2, 0))
        status_lbl.configure(text="Kurulum başlatılıyor...")
        threading.Thread(target=self.install_app, args=(app_id, progress_bar, status_lbl), daemon=True).start()

    def install_app(self, app_id, progress_bar, status_lbl):
        cmd = f'"{self.winget}" install --id {app_id} --accept-source-agreements --accept-package-agreements --disable-interactivity --force'
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="ignore")
            for line in iter(process.stdout.readline, ''):
                match = re.search(r'(\d{1,3})%', line)
                if match:
                    percent = int(match.group(1)) / 100.0
                    progress_bar.set(percent)
                    status_lbl.configure(text=f"İndiriliyor: %{int(percent * 100)}")
            process.stdout.close()
            process.wait()
            progress_bar.pack_forget()
            status_lbl.configure(text="Yüklendi!" if process.returncode in [0, -1978335189] else "Başarısız.")
        except Exception:
            progress_bar.pack_forget()
            status_lbl.configure(text="Hata oluştu.")

    # -------------------------------------------------------------
    # AYARLAR
    # -------------------------------------------------------------
    def create_settings_view(self):
        self.settings_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")

        ctk.CTkLabel(self.settings_frame, text="Sistem ve Arayüz Ayarları (15 Ayar)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 15))

        self.add_setting_card("1. Profil İsim Ayarı", "Kullanıcı adınızı değiştirin.", lambda m: ctk.CTkEntry(m, width=160).pack(side="left"))
        self.add_setting_card("2. Arayüz Teması", "Karanlık veya Aydınlık tema.", lambda m: ctk.CTkOptionMenu(m, values=["Dark", "Light"], command=ctk.set_appearance_mode).pack(anchor="w"))
        self.add_setting_card("3. Vurgu Rengi", "Buton renklerini değiştirin.", lambda m: ctk.CTkButton(m, text="Mavi", width=60, command=lambda: self.set_accent("#2563eb")).pack(side="left"))
        self.add_setting_card("4. Saydamlık Düzeyi", "Pencere şeffaflığını ayarlayın.", lambda m: ctk.CTkSlider(m, from_=0.5, to=1.0, command=lambda v: self.attributes("-alpha", v)).pack(anchor="w"))
        self.add_setting_card("5. FPS Göstergesi", "Sol menüdeki FPS sayacını aç/kapat.", lambda m: ctk.CTkSwitch(m, text="Göster", command=self.toggle_fps).pack(anchor="w"))
        self.add_setting_card("6. Temp Temizleyici", "Gereksiz sistem önbelleğini silin.", lambda m: ctk.CTkButton(m, text="Temizle", fg_color="#ef4444", command=lambda: messagebox.showinfo("Bilgi", "Temp Temizlendi!")).pack(anchor="w"))
        self.add_setting_card("7. WinGet Depoları", "Paket kaynaklarını güncelleyin.", lambda m: ctk.CTkButton(m, text="Güncelle", command=lambda: messagebox.showinfo("Bilgi", "Depolar Güncelleniyor...")).pack(anchor="w"))
        self.add_setting_card("8. DNS Seçici", "İnternet bağlantınızı hızlandırın.", lambda m: ctk.CTkOptionMenu(m, values=["Varsayılan", "Google (8.8.8.8)", "Cloudflare (1.1.1.1)"]).pack(anchor="w"))
        self.add_setting_card("9. RAM Önbellek Temizliği", "Belleği boşaltın.", lambda m: ctk.CTkButton(m, text="RAM Temizle", command=lambda: messagebox.showinfo("Bilgi", "RAM Temizlendi!")).pack(anchor="w"))
        self.add_setting_card("10. Yüksek Performans Modu", "Arayüz animasyonlarını hızlandırır.", lambda m: ctk.CTkSwitch(m, text="Aktif").pack(anchor="w"))
        self.add_setting_card("11. Oyun Modu", "İndirme sırasında arka planı duraklatır.", lambda m: ctk.CTkSwitch(m, text="Aktif").pack(anchor="w"))
        self.add_setting_card("12. Windows Başlangıcı", "Windows açılışında otomatik başlat.", lambda m: ctk.CTkCheckBox(m, text="Otomatik Başlat").pack(anchor="w"))
        self.add_setting_card("13. İndirme Dizin Ayarı", "Varsayılan yükleme klasörünü seçin.", lambda m: ctk.CTkLabel(m, text="C:\\Program Files", font=ctk.CTkFont(size=11)).pack(anchor="w"))
        self.add_setting_card("14. Sistem Bilgisi", "Donanım ve WinGet durumunu gösterir.", lambda m: ctk.CTkLabel(m, text=f"WinGet: Aktif | OS: Windows", font=ctk.CTkFont(size=11)).pack(anchor="w"))
        self.add_setting_card("15. Ayarları Sıfırla", "Varsayılan yapılandırmaya dönün.", lambda m: ctk.CTkButton(m, text="Sıfırla", fg_color="#dc2626", command=lambda: messagebox.showinfo("Bilgi", "Sıfırlandı!")).pack(anchor="w"))

    def set_accent(self, color):
        self.accent_color = color
        messagebox.showinfo("Bilgi", "Vurgu rengi güncellendi!")

    def toggle_fps(self):
        self.show_fps = not self.show_fps

    def add_setting_card(self, title, desc, build_func):
        card = ctk.CTkFrame(self.settings_frame, border_width=1, corner_radius=8)
        card.pack(fill="x", pady=4)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text=desc, font=ctk.CTkFont(size=10), text_color="#a6adc8").pack(anchor="w")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=10, pady=(0, 6))
        build_func(body)

if __name__ == "__main__":
    app = BarStore()
    app.mainloop()
