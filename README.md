# Steam Auto-Restore Watchdog (v1.3) 🏆🛡️

Steam Auto-Restore Watchdog is a lightweight, zero-maintenance background utility that runs silently inside your Windows System Tray. It creates permanent, uncorruptible local achievement backups and uses the official **Steamworks API** to automatically force-unlock and heal your milestones on Valve's live servers if a cloud sync error or glitch ever erases them.

---

## 🚀 Key Features

* **🤖 100% Automated Self-Healing:** Continuously monitors your data. If achievements go missing from your account, the tool interfaces directly with your running Steam client to push them back to the live cloud servers completely hands-free.
* **🎛️ Selective Sync Manager (New in v1.3):** Right-click the system tray icon to launch a sleek, modern, dark-themed configuration checklist. Easily toggle background tracking on or off for individual games.
* **🧼 Zero Clutter Policy:** Features a built-in change-detection engine. It will never spam your hard drive or system resources with duplicate lines or identical file copies. It only saves data when a brand-new milestone is detected.
* **🔒 Total Offline Security:** Scans and processes local Steam directory files (`sharedconfig.vdf`) directly from your machine. No internet required for backups and zero reliance on sensitive Steam Web API keys.

---

## 📂 Project Workspace Structure

To keep your computer completely clean, the app organizes its data in a dedicated folder inside your **Documents** directory:

```text
Documents/
└── SteamWatchdog/
    ├── sync_config.json                 # Remembers your UI game toggle selections
    └── offline_achievements_backup.json  # Your safe, permanent point-of-truth vault
```

---

## 🛠️ Installation & Usage

### For Regular Users (Using the Pre-compiled .exe)
1. Ensure your official **Steam Desktop client** is running and logged in.
2. Head to the **Releases** section on the right side of this page and download `steam_tool.exe`.
3. Double-click the file to start the watchdog. Because it runs as a hidden application, *no console text windows will pop up*.
4. Look at the bottom-right corner of your desktop (near your PC clock) and click the hidden icons arrow (▲).
5. Locate the **Blue Square Icon** to interact with the manual backup, configure the game select lists, or toggle Auto-Mode!

### For Developers (Running from Source)
Because we value open-source transparency, every single line of code can be audited. If you prefer to run or verify the raw code on your machine using Python, run these terminal commands:

```bash
# Install the required automation extensions
pip install plyer pystray Pillow vdf steamworkspy

# Execute the script manually
python steam_tool.py
```

To compile your own console-hidden executable binary from this source:
```bash
pip install pyinstaller
pyinstaller --onefile --noconsole steam_tool.py
```

---

## 📜 License & Trust
This project is 100% free, open-source, and distributed under the **MIT License**. Feel free to fork the repository, inspect the raw scripts, or submit feature requests directly via GitHub Issues!
