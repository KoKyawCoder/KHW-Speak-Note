import os
import zipfile

# Tell SCons what the manifest file is
manifest = "manifest.ini"

# Read the manifest to get the addon name and version
addon_info = {}
with open(manifest, "r", encoding="utf-8") as f:
    for line in f:
        if "=" in line:
            k, v = line.split("=", 1)
            # Use strip() on both key and value to remove whitespaces/quotes
            addon_info[k.strip()] = v.strip().strip('"').strip("'")

addon_name = addon_info.get("name", "khw_speak_note")
addon_version = addon_info.get("version", "1.0.0")
addon_file = f"{addon_name}-{addon_version}.nvda-addon"

def build_addon(target, source, env):
    print(f"Packaging add-on into {addon_file}...")
    with zipfile.ZipFile(str(target[0]), 'w', zipfile.ZIP_DEFLATED) as z:
        # 1. Pack the manifest at the root level
        z.write("manifest.ini", "manifest.ini")
        
        # 2. Pack the CONTENTS of the addon folder, not the folder itself
        for root, dirs, files in os.walk("addon"):
            for file in files:
                filepath = os.path.join(root, file)
                
                # Strip the "addon/" prefix so the file structure starts at root level
                archive_name = os.path.relpath(filepath, "addon")
                
                z.write(filepath, archive_name)
    print("Build complete!")

# Define the SCons build target
env = Environment()
env.Command(addon_file, ["manifest.ini", "addon"], build_addon)