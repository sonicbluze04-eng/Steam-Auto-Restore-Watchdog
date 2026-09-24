import os
import json
import glob
import time
import threading
import vdf
from pathlib import Path
from plyer import notification
import pystray
from PIL import Image, ImageDraw
from steamworks import STEAMWORKS # Hooks into the local running Steam Client Engine

BACKUP_FILE = Path.home() / "Documents" / "offline_achievements_backup.json"
auto_mode_enabled = True

def find_steam_path():
    if os.name == 'nt': 
        return Path("C:/Program Files (x86)/Steam")
    else: 
        return Path(os.path.expanduser("~/.local/share/Steam"))

def fetch_live_achievements():
    """Scans local cache configuration files for unlocked achievements."""
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
    """
    [THE STEAMWORKS BLOCK]: 
    Tells the running local Steam application that a milestone has been earned.
    """
    try:
        # 1. Inform Steamworks which specific game process environment we are tracking
        os.environ["SteamAppId"] = str(app_id)
        
        # 2. Boot up the Steamworks background API wrapper
        sw = STEAMWORKS()
        sw.initialize()
        
        # 3. Trigger the official achievement toggle via the running client socket
        sw.UserStats.SetAchievement(achievement_api_name)
        
        # 4. Command Steam to permanently commit and store the stat on Valve's server database
        sw.UserStats.StoreStats() 
        
        print(f"🎯 Successfully auto-restored: {achievement_api_name} for Game {app_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to auto-inject achievement over Steamworks wrapper: {e}")
        return False

def run_manual_backup(icon=None, item=None):
    live_data = fetch_live_achievements()
    if not live_data:
        notification.notify(title="Steam Tool", message="❌ Could not read Steam achievements.", timeout=5)
        return

    existing_backup = {}
    if BACKUP_FILE.exists():
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            try: existing_backup = json.load(f)
            except Exception: pass

    if live_data == existing_backup:
        notification.notify(title="Steam Tool", message="✨ Backup is already completely up to date!", timeout=5)
        return

    with open(BACKUP_FILE, "w", encoding="utf-8") as out:
        json.dump(live_data, out, indent=4)
    notification.notify(title="Steam Tool", message="✅ Backup updated with latest achievements!", timeout=5)

def toggle_auto_mode(icon, item):
    global auto_mode_enabled
    auto_mode_enabled = not auto_mode_enabled
    status = "ENABLED" if auto_mode_enabled else "DISABLED"
    notification.notify(title="Steam Auto Mode", message=f"Auto background monitor is now {status}.", timeout=4)

def auto_monitor_and_restore_loop():
    """Background thread loop that tracks data loss checkpoints and triggers auto-restoration resets."""
    while True:
        time.sleep(600) # Wait 10 minutes between automated background sweeps
        if not auto_mode_enabled: continue
        if not BACKUP_FILE.exists(): continue

        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            try: saved_backup = json.load(f)
            except Exception: continue

        live_data = fetch_live_achievements()
        restored_count = 0

        # Mismatch Scan Engine: Find lost achievements
        for app_id, saved_achievements in saved_backup.items():
            live_achievements = live_data.get(app_id, {})
            
            for ach_id in saved_achievements.keys():
                # Item found in local Document backup vaults but gone from Steam cache directories
                if ach_id not in live_achievements:
                    # Fire the automated Steamworks background unlock trigger function
                    success = force_inject_achievement(app_id, ach_id)
                    if success:
                        restored_count += 1

        if restored_count > 0:
            notification.notify(
                title="🛡️ Auto-Restore Successful!",
                message=f"Detected data loss! Automatically pushed {restored_count} achievements back to Steam.",
                timeout=10
            )
            continue

        # Check for new unlocks to expand backup file histories
        has_new_data = False
        for app_id, live_achievements in live_data.items():
            if app_id not in saved_backup:
                saved_backup[app_id] = {}
                has_new_data = True
            for ach_id, status in live_achievements.items():
                if ach_id not in saved_backup[app_id]:
                    saved_backup[app_id][ach_id] = status
                    has_new_data = True

        if has_new_data:
            with open(BACKUP_FILE, "w", encoding="utf-8") as out:
                json.dump(saved_backup, out, indent=4)

def create_tray_icon():
    image = Image.new('RGB', (64, 64), color=(0, 128, 255))
    d = ImageDraw.Draw(image)
    d.rectangle([(16, 16), (48, 48)], fill=(255, 255, 255))
    
    menu = pystray.Menu(
        pystray.MenuItem("Backup Right Now", run_manual_backup),
        pystray.MenuItem("Enable Auto Mode", toggle_auto_mode, checked=lambda item: auto_mode_enabled),
        pystray.MenuItem("Exit Tool", lambda icon, item: icon.stop())
    )
    icon = pystray.Icon("SteamAutoRestore", image, "Steam Smart Auto-Restore", menu)
    icon.run()

if __name__ == "__main__":
    monitor_thread = threading.Thread(target=auto_monitor_and_restore_loop, daemon=True)
    monitor_thread.start()
    create_tray_icon()
