import os
import json
import glob
import time
import threading
import vdf
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from plyer import notification
import pystray
from PIL import Image, ImageDraw
from steamworks import STEAMWORKS

# Paths Setup
DOCS_DIR = Path.home() / "Documents" / "SteamWatchdog"
DOCS_DIR.mkdir(exist_ok=True)
BACKUP_FILE = DOCS_DIR / "offline_achievements_backup.json"
CONFIG_FILE = DOCS_DIR / "sync_config.json"

auto_mode_enabled = True

def load_sync_config():
    """Loads the user's enabled/disabled game choices."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            try: return json.load(f)
            except Exception: pass
    return {}

def save_sync_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def find_steam_path():
    if os.name == 'nt': return Path("C:/Program Files (x86)/Steam")
    return Path(os.path.expanduser("~/.local/share/Steam"))

def fetch_live_achievements():
    steam_path = find_steam_path()
    if not steam_path.exists(): return {}
    userdata_path = steam_path / "userdata"
    if not userdata_path.exists(): return {}

    search_pattern = os.path.join(userdata_path, "*", "7", "remote", "sharedconfig.vdf")
    vdf_files = glob.glob(search_pattern)

    live_data = {}
    for vdf_path in vdf_files:
        with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
            try:
                data = vdf.load(f)
                apps = data.get("UserRoamingConfigStore", {}).get("Software", {}).get("Valve", {}).get("Steam", {}).get("Apps", {})
                for app_id, app_data in apps.items():
                    achievements = app_data.get("Achievements", {})
                    if achievements:
                        unlocked = {k: v for k, v in achievements.items() if str(v) != "0"}
                        if unlocked:
                            live_data[app_id] = unlocked
            except Exception: pass
    return live_data

def force_inject_achievement(app_id, achievement_api_name):
    try:
        os.environ["SteamAppId"] = str(app_id)
        sw = STEAMWORKS()
        sw.initialize()
        sw.UserStats.SetAchievement(achievement_api_name)
        sw.UserStats.StoreStats() 
        return True
    except Exception:
        return False

def open_config_ui():
    """Pops up a clean, modern UI layout for selecting games to monitor."""
    live_games = fetch_live_achievements().keys()
    saved_config = load_sync_config()

    root = tk.Tk()
    root.title("Watchdog Sync Manager v1.3")
    root.geometry("400x450")
    root.resizable(False, False)
    root.configure(bg="#1e1e2e") # Deep dark theme background

    # Title Banner
    lbl = tk.Label(root, text="Select Games to Monitor:", font=("Arial", 12, "bold"), fg="#cdd6f4", bg="#1e1e2e")
    lbl.pack(pady=10)

    # Scrollable Frame list container
    canvas = tk.Canvas(root, bg="#1e1e2e", highlightthickness=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#1e1e2e")

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=15, pady=5)
    scrollbar.pack(side="right", fill="y", pady=5)

    checkbox_vars = {}
    for app_id in sorted(live_games):
        # Default setting: True unless explicitly disabled by user earlier
        is_checked = saved_config.get(app_id, True)
        var = tk.BooleanVar(value=is_checked)
        checkbox_vars[app_id] = var

        # Use clean styling for check buttons
        cb = tk.Checkbutton(
            scroll_frame, 
            text=f"Game AppID: {app_id}", 
            variable=var, 
            font=("Arial", 10),
            fg="#cdd6f4", 
            bg="#1e1e2e", 
            selectcolor="#313244", 
            activebackground="#1e1e2e", 
            activeforeground="#a6e3a1"
        )
        cb.pack(anchor="w", pady=4, padx=5)

    def save_and_close():
        new_config = {app_id: var.get() for app_id, var.get in checkbox_vars.items()}
        save_sync_config(new_config)
        root.destroy()
        notification.notify(title="Watchdog Config", message="⚙️ Game synchronization filters successfully updated!", timeout=4)

    # Save button configuration layout
    btn = tk.Button(root, text="Save Configurations", command=save_and_close, font=("Arial", 10, "bold"), fg="#11111b", bg="#a6e3a1", activebackground="#94e2d5")
    btn.pack(pady=15)
    root.mainloop()

def run_manual_backup(icon=None, item=None):
    live_data = fetch_live_achievements()
    if not live_data: return

    # Apply configuration filter mask rule checks
    sync_config = load_sync_config()
    filtered_data = {k: v for k, v in live_data.items() if sync_config.get(k, True)}

    with open(BACKUP_FILE, "w", encoding="utf-8") as out:
        json.dump(filtered_data, out, indent=4)
    notification.notify(title="Steam Watchdog", message="✅ Filtered offline backup successfully updated!", timeout=4)

def auto_monitor_and_restore_loop():
    while True:
        time.sleep(600)
        if not auto_mode_enabled or not BACKUP_FILE.exists(): continue

        sync_config = load_sync_config()
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            try: saved_backup = json.load(f)
            except Exception: continue

        live_data = fetch_live_achievements()
        restored_count = 0

        for app_id, saved_achievements in saved_backup.items():
            # SKIP target processing entirely if user toggled the game toggle check to FALSE
            if not sync_config.get(app_id, True): continue

            live_achievements = live_data.get(app_id, {})
            for ach_id in saved_achievements.keys():
                if ach_id not in live_achievements:
                    if force_inject_achievement(app_id, ach_id):
                        restored_count += 1

        if restored_count > 0:
            notification.notify(title="🛡️ Auto-Restore Triggered", message=f"Restored {restored_count} achievements back to Steam profiles!", timeout=10)

def create_tray_icon():
    image = Image.new('RGB', (64, 64), color=(30, 144, 255))
    d = ImageDraw.Draw(image)
    d.rectangle([(16, 16), (48, 48)], fill=(255, 255, 255))
    
    menu = pystray.Menu(
        pystray.MenuItem("Backup Right Now", run_manual_backup),
        pystray.MenuItem("Configure Sync List...", lambda icon, item: threading.Thread(target=open_config_ui).start()),
        pystray.MenuItem("Enable Auto Mode", lambda icon, item: globals().update(auto_mode_enabled=not auto_mode_enabled), checked=lambda item: auto_mode_enabled),
        pystray.MenuItem("Exit Tool", lambda icon, item: icon.stop())
    )
    icon = pystray.Icon("SteamWatchdogv13", image, "Steam Watchdog v1.3", menu)
    icon.run()

if __name__ == "__main__":
    threading.Thread(target=auto_monitor_and_restore_loop, daemon=True).start()
    create_tray_icon()
