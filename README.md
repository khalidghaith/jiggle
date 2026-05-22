# Jiggle (1.0.0)

Jiggle is a lightweight, premium desktop utility built with Python (Tkinter) that monitors system inactivity and simulates human-like inputs (mouse movements, page scrolling, and keypresses) to keep your system active and prevent it from falling asleep or showing as idle.

---

## ✨ Features

- **Activity Detection**: Uses global input listeners to monitor mouse and keyboard activity.
- **Human-like Input Simulation**:
  - **Mouse Movement**: Randomly moves the cursor within a controlled, safe boundary relative to your starting cursor position (no screen-wide drift).
  - **Page Scroll**: Simulates natural page scrolling (up and down).
  - **Key Press**: Triggers standard keypresses (e.g., `Shift`) safely.
- **Dynamic Inactivity Threshold**: Customize the idle duration before the jiggler triggers.
- **Interactive GUI**: A modern pastel-themed user interface with collapsible/expandable settings.
- **System Tray Integration**:
  - Minimize to the Windows System Tray to run silently in the background.
  - Interactive right-click menu with options to show the window or exit.
  - Notifications indicating when it's running in the background.
- **Windows Startup Registry Support**: Optional integration during installation to run automatically on Windows boot.
- **Single-Instance Enforcement**: Binds to a local port. If you try to open Jiggle while it is already running, the active window will automatically restore and flash to the front.

---

## 🛠️ Tech Stack & Dependencies

- **Core**: Python 3.x
- **GUI Framework**: Tkinter
- **System Automation**:
  - `pynput` (for monitoring and simulating inputs)
- **System Tray & Image Drawing**:
  - `pystray` (for tray notifications and menu)
  - `Pillow` (for icon rendering)

---

## 🚀 Running Locally

1. Clone this repository to your local machine:
   ```bash
   git clone <your-repository-url>
   cd jiggle
   ```

2. Install the required dependencies:
   ```bash
   pip install pynput pystray Pillow
   ```

3. Launch the application:
   ```bash
   python jiggle_app.py
   ```

---

## 📦 Building Standalone Executable (.exe)

You can compile Jiggle into a single, standalone Windows `.exe` using PyInstaller.

A helper batch script (`build_exe.bat`) is included in the project:
1. Double-click **`build_exe.bat`** OR run it via terminal:
   ```cmd
   build_exe.bat
   ```
2. Once complete, you will find a standalone `Jiggle.exe` in the `dist/` directory.

---

## 💾 Creating the Installer (Inno Setup)

To package Jiggle into a professional Windows Installer:
1. Make sure you have [Inno Setup](https://jrsoftware.org/isinfo.php) installed on your PC.
2. Compile the `setup_script.iss` script inside Inno Setup.
3. This creates a standard `Jiggle_Setup.exe` inside the `installer_output/` folder, which installs the app into `Program Files`, adds standard shortcut icons, creates a clean uninstaller that sweeps away configuration registries, and handles automatic run-at-startup preferences.

---

## 📄 License

This project is licensed under the MIT License.
