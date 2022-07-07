
import os
import shutil

from src import version

if os.path.exists("dist"):
    shutil.rmtree("dist")

os.system("pyinstaller src/modmerger.py")

shutil.copyfile("src/original.gdcc", "dist/modmerger/original.gdcc")
shutil.copyfile("README.md", "dist/README.md")
os.mkdir("dist/mods")
os.mkdir("dist/output")

shutil.make_archive("thehunter-mod-merger-%s-win64" % version.VERSION, "zip", root_dir="dist")

shutil.rmtree("dist")
shutil.rmtree("build")
os.remove("modmerger.spec")
