import tkinter as tk
from tkinter import font as tkfont, messagebox
import time
import threading
import random
import os
import sys
import json
import socket
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# --- New Imports for System Tray ---
import pystray
from PIL import Image, ImageDraw

def resource_path(relative_path):
    """ Get absolute path to resource (for read-only assets like icons) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_config_dir():
    """ 
    Get path for writable config directory in AppData.
    """
    app_data = os.getenv('LOCALAPPDATA')
    if not app_data:
        app_data = os.path.expanduser("~") 
        
    config_dir = os.path.join(app_data, "JiggleMonitor")
    
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError:
            pass 
            
    return config_dir

def get_config_path():
    """ Get full path to the config file. """
    return os.path.join(get_config_dir(), "config.json")

def create_fallback_image():
    """Generates a simple colored box icon if icon.ico is missing."""
    width = 64
    height = 64
    color1 = "black"
    color2 = "#A8E6CF" # Pastel green
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, 3 * width // 4, 3 * width // 4), fill=color2)
    return image

# --- Core Jiggle Logic ---
class JiggleEngine:
    def __init__(self, app_reference, interval=30):
        self.app = app_reference
        self.interval = interval
        self.intensity = 50           
        self._jiggle_active = False
        self._thread = None
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        self.enable_move = True
        self.enable_scroll = True
        self.enable_key = True
        
        self.MAX_STEP = 15    
        self.MIN_SLEEP = 0.5  
        self.MAX_SLEEP = 2.0  

    def set_capabilities(self, move, scroll, key):
        self.enable_move = move
        self.enable_scroll = scroll
        self.enable_key = key

    def start_jiggling(self):
        if self._thread and self._thread.is_alive():
            return False

        if not self._jiggle_active:
            self._jiggle_active = True
            self._thread = threading.Thread(target=self._jiggle_loop, daemon=True)
            self._thread.start()
            return True
        return False

    def stop_jiggling(self):
        self._jiggle_active = False
        return True

    def _jiggle_loop(self):
        try:
            center_x, center_y = self.mouse.position
        except:
            self._jiggle_active = False
            return

        half_intensity = self.intensity / 2

        while self._jiggle_active:
            try:
                allowed_actions = []
                allowed_weights = []
                
                if self.enable_move:
                    allowed_actions.append('move')
                    allowed_weights.append(70) 
                
                if self.enable_scroll:
                    allowed_actions.append('scroll')
                    allowed_weights.append(20)
                    
                if self.enable_key:
                    allowed_actions.append('key')
                    allowed_weights.append(10) 

                if not allowed_actions:
                    time.sleep(1)
                    continue

                action = random.choices(allowed_actions, weights=allowed_weights, k=1)[0]

                self.app.programmatic_move = True
                
                if action == 'move':
                    step_x = random.randint(-self.MAX_STEP, self.MAX_STEP)
                    step_y = random.randint(-self.MAX_STEP, self.MAX_STEP)
                    current_x, current_y = self.mouse.position
                    
                    new_x = current_x + step_x
                    new_y = current_y + step_y
                    
                    # Keep movement constrained around the initial center
                    new_x = max(center_x - half_intensity, min(center_x + half_intensity, new_x))
                    new_y = max(center_y - half_intensity, min(center_y + half_intensity, new_y))
                    
                    self.mouse.position = (new_x, new_y)
                
                elif action == 'scroll':
                    scroll_dir = random.choice([1, -1]) 
                    self.mouse.scroll(0, scroll_dir)
                    
                elif action == 'key':
                    # Simulate a key press/release (e.g., Shift) to prevent idle status
                    self.keyboard.press(Key.shift)
                    self.keyboard.release(Key.shift)

                time.sleep(0.1) # Short delay to ensure action registers
                self.app.programmatic_move = False
                
                # Wait for the next jiggle
                sleep_time = random.uniform(self.MIN_SLEEP, self.MAX_SLEEP)
                time.sleep(sleep_time)

            except Exception as e:
                print(f"Simulation Error: {e}")
                self.app.programmatic_move = False
                self._jiggle_active = False
                break
        
        self.app.programmatic_move = False

# --- GUI Application ---
class JiggleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Jiggle Monitor")
        self.geometry("440x320") 
        self.resizable(False, False)
        
        # --- Config File Setup ---
        self.config_file = get_config_path()

        # --- Icon Setup ---
        self.icon_path = resource_path("icon.ico")
        try:
            if os.path.exists(self.icon_path):
                self.iconbitmap(self.icon_path)
        except Exception as e:
            print(f"Could not load window icon: {e}")

        # -- State Variables --
        self.monitoring_active = False  
        self.last_activity_time = time.time()
        self.programmatic_move = False  
        self.settings_visible = False
        self.app_running = True 
        self.has_shown_tray_message = False 
        self.saved_settings = {} # Store last saved state
        
        self.engine = JiggleEngine(self, interval=99999) 
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # -- Initialize Variables (Updated Defaults) --
        self.var_threshold = tk.IntVar(value=30)      
        self.var_enable_move = tk.BooleanVar(value=True)
        self.var_enable_scroll = tk.BooleanVar(value=True)
        self.var_enable_key = tk.BooleanVar(value=True)
        self.var_start_minimized = tk.BooleanVar(value=True) 
        self.var_start_monitoring = tk.BooleanVar(value=False) 

        # Add listeners for changes
        self.var_threshold.trace_add("write", self._on_setting_changed)
        self.var_enable_move.trace_add("write", self._on_setting_changed)
        self.var_enable_scroll.trace_add("write", self._on_setting_changed)
        self.var_enable_key.trace_add("write", self._on_setting_changed)
        self.var_start_minimized.trace_add("write", self._on_setting_changed)
        self.var_start_monitoring.trace_add("write", self._on_setting_changed) 

        # -- Load Settings from JSON --
        self._load_settings()

        self._configure_styles()
        self._create_widgets()
        
        # Check for startup launch flag
        is_startup_launch = "--startup" in sys.argv
        
        # 1. Handle Minimizing
        if is_startup_launch and self.var_start_minimized.get():
            self.withdraw()

        # 2. Handle Auto-Monitoring (only if launched via startup AND setting is enabled)
        if is_startup_launch and self.var_start_monitoring.get():
            # FIX: Use a robust way to start monitoring on startup
            # Start monitoring must be called after Tkinter is fully initialized.
            self.after(500, self._toggle_monitoring) 
            
        self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        
        # Start the system tray thread
        self.tray_thread = threading.Thread(target=self._start_tray_icon, daemon=True)
        self.tray_thread.start()

    def _configure_styles(self):
        self.PASTEL_BG = "#F3F7F8"    
        self.PASTEL_ACCENT = "#A9D0E6" 
        self.PASTEL_GREEN = "#A8E6CF"  
        self.PASTEL_RED = "#FFADAD"
        self.PASTEL_SETTINGS = "#E8ECEF"
        self.PASTEL_DISABLED = "#E0E0E0"
        self.TEXT_DARK = "#333333"     
        self.TEXT_ERROR = "#D9534F"
        self.TEXT_SUCCESS = "#5CB85C"
        self.TEXT_DISABLED = "#888888"

        self.custom_font = tkfont.Font(family="Helvetica", size=14, weight="bold") 
        self.status_font = tkfont.Font(family="Helvetica", size=20, weight="bold") 
        self.detail_font = tkfont.Font(family="Helvetica", size=10)
        
        self.config(bg=self.PASTEL_BG) 

    def _create_widgets(self):
        self.main_frame = tk.Frame(self, bg=self.PASTEL_BG, padx=40, pady=20)
        self.main_frame.pack(side="top", fill="both", expand=True)

        self.status_label = tk.Label(
            self.main_frame,
            text="STOPPED",
            font=self.status_font,
            fg="#9E9E9E",
            bg=self.PASTEL_BG
        )
        self.status_label.pack(pady=(10, 5))
        
        self.detail_label = tk.Label(
            self.main_frame,
            text="Ready to monitor.",
            font=self.detail_font,
            fg=self.TEXT_DARK,
            bg=self.PASTEL_BG
        )
        self.detail_label.pack(pady=(0, 20))

        self.toggle_button = tk.Button(
            self.main_frame,
            text="START MONITORING",
            command=self._toggle_monitoring,
            width=25,
            height=2,
            bd=0,
            relief=tk.FLAT,
            bg=self.PASTEL_GREEN,
            fg=self.TEXT_DARK,
            font=self.custom_font,
            activebackground="#8ED8B7",
            cursor="hand2",
            padx=10,
            pady=10
        )
        self.toggle_button.pack(pady=10)
        
        self.settings_btn = tk.Button(
            self.main_frame, 
            text="▼ Settings", 
            command=self._toggle_settings_panel,
            font=self.detail_font,
            bd=0,
            relief=tk.FLAT,
            bg=self.PASTEL_BG,
            fg="#555555",
            activebackground=self.PASTEL_BG,
            cursor="hand2"
        )
        self.settings_btn.pack(pady=(20, 0), anchor="s")

        self.settings_frame = tk.Frame(self.main_frame, bg=self.PASTEL_SETTINGS, padx=15, pady=15, relief=tk.RIDGE, bd=0)
        
        # Idle Timeout
        tk.Label(self.settings_frame, text="Idle Timeout (seconds):", bg=self.PASTEL_SETTINGS, font=self.detail_font).pack(anchor='w')
        tk.Entry(self.settings_frame, textvariable=self.var_threshold, width=10, bd=1, relief=tk.SUNKEN, font=self.detail_font).pack(anchor='w', pady=(2, 10))

        # Simulation Toggles
        toggles_frame = tk.Frame(self.settings_frame, bg=self.PASTEL_SETTINGS)
        toggles_frame.pack(fill='x', pady=(5, 5))
        
        tk.Label(toggles_frame, text="Simulation Actions:", bg=self.PASTEL_SETTINGS, font=("Helvetica", 10, "bold"), fg="#555").pack(anchor='w', pady=(0, 5))

        cb_style = {
            "bg": self.PASTEL_SETTINGS, 
            "activebackground": self.PASTEL_SETTINGS, 
            "font": self.detail_font, 
            "fg": self.TEXT_DARK, 
            "selectcolor": "white",
            "bd": 0
        }

        tk.Checkbutton(toggles_frame, text="Mouse Movement", variable=self.var_enable_move, **cb_style).pack(anchor='w')
        tk.Checkbutton(toggles_frame, text="Page Scroll", variable=self.var_enable_scroll, **cb_style).pack(anchor='w')
        tk.Checkbutton(toggles_frame, text="Key Press (Shift)", variable=self.var_enable_key, **cb_style).pack(anchor='w')

        # Startup Options
        tk.Label(toggles_frame, text="Startup Options:", bg=self.PASTEL_SETTINGS, font=("Helvetica", 10, "bold"), fg="#555").pack(anchor='w', pady=(10, 5))

        tk.Checkbutton(toggles_frame, text="Start Minimized to Tray", variable=self.var_start_minimized, **cb_style).pack(anchor='w')
        tk.Checkbutton(toggles_frame, text="Start Monitoring on Startup", variable=self.var_start_monitoring, **cb_style).pack(anchor='w')


        self.feedback_label = tk.Label(self.settings_frame, text="", bg=self.PASTEL_SETTINGS, font=("Helvetica", 9), fg=self.TEXT_DARK)
        self.feedback_label.pack(pady=(5, 5))

        # Apply Button - Initial state is disabled (greyed out)
        self.apply_btn = tk.Button(
            self.settings_frame,
            text="Apply Changes",
            command=self._apply_settings_inline,
            bg=self.PASTEL_DISABLED,
            fg=self.TEXT_DISABLED,
            state="disabled",
            bd=0,
            relief=tk.FLAT,
            font=("Helvetica", 10, "bold"),
            padx=10,
            pady=5,
            cursor="arrow"
        )
        self.apply_btn.pack(fill='x')

    # --- Config / Persistence Logic ---
    def _load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.var_threshold.set(data.get("threshold", 30))
                    self.var_enable_move.set(data.get("move", True))
                    self.var_enable_scroll.set(data.get("scroll", True))
                    self.var_enable_key.set(data.get("key", True))
                    self.var_start_minimized.set(data.get("start_minimized", True))
                    self.var_start_monitoring.set(data.get("start_monitoring", False))
                    
                    self.engine.set_capabilities(
                        data.get("move", True),
                        data.get("scroll", True),
                        data.get("key", True)
                    )
                    self.idle_threshold = data.get("threshold", 30)
            else:
                self.idle_threshold = 30
        except Exception as e:
            print(f"Error loading config: {e}")
            self.idle_threshold = 30
        
        # Save baseline to check against for button highlighting
        self._update_saved_snapshot()

    def _update_saved_snapshot(self):
        """Update the internal snapshot of saved settings."""
        self.saved_settings = {
            "threshold": self.var_threshold.get(),
            "move": self.var_enable_move.get(),
            "scroll": self.var_enable_scroll.get(),
            "key": self.var_enable_key.get(),
            "start_minimized": self.var_start_minimized.get(),
            "start_monitoring": self.var_start_monitoring.get() 
        }
        # Reset button state
        if hasattr(self, 'apply_btn'):
            self.apply_btn.config(
                bg=self.PASTEL_DISABLED, 
                fg=self.TEXT_DISABLED, 
                state="disabled",
                cursor="arrow"
            )

    def _on_setting_changed(self, *args):
        """Called whenever a settings variable changes."""
        if not hasattr(self, 'apply_btn'): return
        
        current_state = {
            "threshold": self.var_threshold.get(),
            "move": self.var_enable_move.get(),
            "scroll": self.var_enable_scroll.get(),
            "key": self.var_enable_key.get(),
            "start_minimized": self.var_start_minimized.get(),
            "start_monitoring": self.var_start_monitoring.get() 
        }
        
        if current_state != self.saved_settings:
            # Highlight button
            self.apply_btn.config(
                bg=self.PASTEL_ACCENT, 
                fg="white", 
                state="normal",
                cursor="hand2"
            )
        else:
            # Dim button
            self.apply_btn.config(
                bg=self.PASTEL_DISABLED, 
                fg=self.TEXT_DISABLED, 
                state="disabled",
                cursor="arrow"
            )

    def _save_settings(self):
        data = {
            "threshold": self.var_threshold.get(),
            "move": self.var_enable_move.get(),
            "scroll": self.var_enable_scroll.get(),
            "key": self.var_enable_key.get(),
            "start_minimized": self.var_start_minimized.get(),
            "start_monitoring": self.var_start_monitoring.get() 
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
            # Update baseline
            self._update_saved_snapshot()
        except Exception as e:
            print(f"Error saving config: {e}")

    # --- System Tray Logic ---
    def _start_tray_icon(self):
        try:
            if os.path.exists(self.icon_path):
                image = Image.open(self.icon_path)
            else:
                image = create_fallback_image()
        except Exception:
            image = create_fallback_image()

        menu = pystray.Menu(
            pystray.MenuItem("Show Jiggle Monitor", self._restore_window, default=True),
            pystray.MenuItem("Exit", self._quit_application)
        )

        self.tray_icon = pystray.Icon("JiggleMonitor", image, "Jiggle Monitor", menu)
        self.tray_icon.run()

    def _minimize_to_tray(self):
        self.withdraw()
        if not self.has_shown_tray_message:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.notify(
                    "Still running in the background.\nDouble-click to restore.",
                    "Jiggle Monitor"
                )
            self.has_shown_tray_message = True
        
    def _restore_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, lambda: self.attributes('-topmost', True))
        self.after(0, lambda: self.attributes('-topmost', False))

    def _quit_application(self, icon=None, item=None):
        self.app_running = False
        if icon:
            icon.stop()
        self.after(0, self._perform_shutdown)

    def _perform_shutdown(self):
        self.monitoring_active = False
        self.engine.stop_jiggling()
        self._stop_listeners()
        self.destroy() 

    # --- Core Monitoring Logic ---
    def _monitor_loop(self):
        if not self.app_running: return 
        if not self.monitoring_active: return

        current_time = time.time()
        elapsed = current_time - self.last_activity_time
        remaining = max(0, self.idle_threshold - elapsed)

        is_jiggling = self.engine._jiggle_active

        if is_jiggling:
            self.status_label.config(text="SIMULATION ACTIVE", fg=self.PASTEL_RED)
            self.detail_label.config(text="Simulating work...")
        else:
            if elapsed > self.idle_threshold:
                self.engine.start_jiggling()
            else:
                self.status_label.config(text="MONITORING", fg=self.PASTEL_GREEN)
                self.detail_label.config(text=f"Waiting for inactivity... {int(remaining)}s")

        self.after(500, self._monitor_loop)

    def _handle_user_input(self, *args):
        if self.programmatic_move:
            return

        self.last_activity_time = time.time()

        if self.engine._jiggle_active:
            self.after(0, self.engine.stop_jiggling)

    # --- Listeners ---
    def _start_listeners(self):
        if not self.mouse_listener or not self.mouse_listener.running:
            self.mouse_listener = mouse.Listener(
                on_move=lambda x, y: self._handle_user_input(),
                on_click=lambda x, y, button, pressed: self._handle_user_input() if pressed else None,
                on_scroll=lambda x, y, dx, dy: self._handle_user_input() if (dx or dy) else None
            )
            self.mouse_listener.start()

        if not self.keyboard_listener or not self.keyboard_listener.running:
            self.keyboard_listener = keyboard.Listener(
                on_press=lambda key: self._handle_user_input()
            )
            self.keyboard_listener.start()

    def _stop_listeners(self):
        if self.mouse_listener and self.mouse_listener.running:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.keyboard_listener and self.keyboard_listener.running:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    # --- Control Flow ---
    def _toggle_monitoring(self):
        if self.monitoring_active:
            self.monitoring_active = False
            self.engine.stop_jiggling()
            self._stop_listeners()
            
            self.toggle_button.config(text="START MONITORING", bg=self.PASTEL_GREEN, fg=self.TEXT_DARK)
            self.status_label.config(text="STOPPED", fg="#9E9E9E")
            self.detail_label.config(text="Monitoring paused.")
        else:
            self.monitoring_active = True
            self.last_activity_time = time.time() 
            self._start_listeners()
            self._monitor_loop() 
            
            self.toggle_button.config(text="STOP MONITORING", bg=self.PASTEL_RED, fg="white")

    # --- Settings Logic ---
    def _toggle_settings_panel(self):
        if self.settings_visible:
            self.settings_frame.pack_forget()
            self.settings_btn.config(text="▼ Settings")
            self.geometry("440x320") 
            self.settings_visible = False
            self.feedback_label.config(text="") 
        else:
            self.settings_frame.pack(fill='x', pady=10)
            self.settings_btn.config(text="▲ Hide Settings")
            self.geometry("440x630") 
            self.settings_visible = True

    def _apply_settings_inline(self):
        try:
            new_thresh = self.var_threshold.get()
            # Enforce minimum idle time of 5 seconds
            if new_thresh < 5:
                self.feedback_label.config(text="Error: Minimum timeout is 5 seconds.", fg=self.TEXT_ERROR)
                return
            self.idle_threshold = new_thresh
        except:
            self.feedback_label.config(text="Error: Invalid Timeout", fg=self.TEXT_ERROR)
            return
        
        self.engine.set_capabilities(
            move=self.var_enable_move.get(),
            scroll=self.var_enable_scroll.get(),
            key=self.var_enable_key.get()
        )

        self._save_settings()

        self.feedback_label.config(text="Settings Saved ✓", fg=self.TEXT_SUCCESS)
        self.after(2000, lambda: self.feedback_label.config(text=""))

# --- SINGLE INSTANCE LOGIC (SOCKET BASED) ---
SINGLE_INSTANCE_PORT = 65432 # Port to listen on

def check_single_instance():
    """
    Returns the server socket if this is the first instance.
    If another instance is running, sends 'SHOW' and returns None.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to localhost port
        s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.listen(1)
        return s 
    except OSError:
        # Port is in use, another instance exists
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
            client.sendall(b"SHOW")
            client.close()
        except:
            pass # Failed to signal, maybe zombie process
        return None

def listen_for_instances(server_socket, app_instance):
    """Background thread to listen for second instances trying to start."""
    while True:
        try:
            conn, addr = server_socket.accept()
            data = conn.recv(1024)
            if b"SHOW" in data:
                # Trigger window restore on main thread
                app_instance.after(0, app_instance._restore_window)
            conn.close()
        except:
            break

if __name__ == "__main__":
    # Check for existing instance
    server_sock = check_single_instance()
    
    if server_sock:
        # We are the main instance
        try:
            app = JiggleApp()
            
            # Start listener thread
            listener = threading.Thread(target=listen_for_instances, args=(server_sock, app), daemon=True)
            listener.start()
            
            app.mainloop()
        except ImportError:
             # Dependency fallback
             import tkinter.messagebox
             root = tk.Tk()
             root.withdraw()
             tkinter.messagebox.showerror("Missing Dependency", "Please install dependencies:\npip install pynput pystray Pillow")
             root.destroy()
        finally:
            server_sock.close()
    else:
        # Another instance is running; we sent the signal and now exit.
        sys.exit(0)