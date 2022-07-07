
import os
import shutil

VERSION = "0.1.0"

if os.path.exists("dist"):
    shutil.rmtree("dist")

os.system("pyinstaller --onefile src/modmerger.py")

shutil.copyfile("src/original.gdcc", "dist/original.gdcc")
shutil.copyfile("README.md", "dist/README.md")
os.mkdir("dist/mods")

shutil.make_archive("thehunter-mod-merger-%s" % VERSION, "zip", root_dir="dist")

shutil.rmtree("dist")
shutil.rmtree("build")
os.remove("modmerger.spec")
