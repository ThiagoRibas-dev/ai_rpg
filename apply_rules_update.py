import os


def sanitize_imports():
    # 1. RESET app/gui/__init__.py
    # It likely contains references to MainView or Managers which are gone.
    gui_init = os.path.join("app", "gui", "__init__.py")
    if os.path.exists(gui_init):
        print(f"🧹 Resetting {gui_init}...")
        with open(gui_init, "w", encoding="utf-8") as f:
            f.write('"""\nGUI Package.\n"""\n')

    # 2. DEFINE FORBIDDEN STRINGS
    # If any file contains these strings, it will likely crash.
    forbidden_imports = [
        "app.gui.main_view",
        "app.gui.managers",
        "app.gui.builders",
        "app.gui.panels",
        "app.gui.styles",  # Replaced by app.gui.theme
        "app.gui.utils",
        "customtkinter",  # We are fully NiceGUI now
    ]

    print("\n🔍 Scanning codebase for lingering legacy imports...")

    found_issues = False

    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)

                # Skip the script itself if it's in the tree
                if "sanitize" in path:
                    continue

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    for bad_import in forbidden_imports:
                        if bad_import in content:
                            print(f"   ⚠️  WARNING: Found '{bad_import}' in {path}")
                            found_issues = True

                            # Auto-fix specific common cases?
                            # For now, just reporting is safer than regex replacing blindly.
                except Exception as e:
                    print(f"   Error reading {path}: {e}")

    if not found_issues:
        print("✅ No legacy imports found. The code looks clean.")
    else:
        print("\n❌ Issues found! Please manually check the files listed above.")


if __name__ == "__main__":
    sanitize_imports()
