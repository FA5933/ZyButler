# Building ZyButler GUI as an Executable

## Prerequisites
- Python 3.12 installed
- PyInstaller installed: `py -m pip install pyinstaller`

## Important: Remove Incompatible Packages
Before building, ensure obsolete packages are removed:
```cmd
py -m pip uninstall -y pathlib enum34
```

## Build Instructions

### Method 1: Using the Full Python Path (Recommended)
```cmd
C:\Users\ms1322\AppData\Local\Programs\Python\Python312\python.exe -m PyInstaller --onefile --windowed --hidden-import=ZyButler zybutler_gui.py
```

### Method 2: Using py Launcher
```cmd
py -m PyInstaller --onefile --windowed --hidden-import=ZyButler zybutler_gui.py
```

## Build Output
- The executable will be created in: `dist\zybutler_gui.exe`
- Build files will be in: `build\`
- Spec file will be created: `zybutler_gui.spec`

## Running the Executable
```cmd
.\dist\zybutler_gui.exe
```

## Troubleshooting

### Issue: PyInstaller produces no output
**Solution**: Check for obsolete packages like `pathlib` and `enum34`:
```cmd
py -m pip uninstall -y pathlib enum34
```

### Issue: Missing dependencies
**Solution**: Add hidden imports:
```cmd
py -m PyInstaller --onefile --windowed --hidden-import=ZyButler --hidden-import=tkinter zybutler_gui.py
```

### Issue: Application crashes on startup
**Solution**: Run without `--windowed` flag to see error output:
```cmd
py -m PyInstaller --onefile --hidden-import=ZyButler zybutler_gui.py
```

## Clean Build
To perform a clean build, delete existing build artifacts:
```cmd
rmdir /s /q build dist
del zybutler_gui.spec
```

Then rebuild using one of the methods above.

## Distribution
The `zybutler_gui.exe` file in the `dist` folder is a standalone executable that can be distributed and run on any Windows machine without requiring Python to be installed.

### Dependencies Bundled
- Python 3.12 runtime
- tkinter (GUI framework)
- ZyButler.py (main logic module)
- All required standard library modules

### System Requirements
- Windows 10 or later
- No additional software required (Python not needed on target machine)
- For device detection: ADB (Android Debug Bridge) must be installed and in PATH

