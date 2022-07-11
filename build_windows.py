
import os
import shutil
import struct

from src import version

BITS = struct.calcsize("P") * 8

if os.path.exists("dist"):
    shutil.rmtree("dist")

os.system("pipenv run pyinstaller src/modmerger.py")

if True:
    #A bit of a hack: unzip the "base_library.zip" into an actual directory called "base_library.zip".
    #This is because some file services etc. will reject .zip files containing other .zip-files...
    #The Python sys.path import machinery should still work just the same.
    os.system("python -m zipfile -e dist/modmerger/base_library.zip dist/modmerger/base_library_temp")
    os.remove("dist/modmerger/base_library.zip")
    os.rename("dist/modmerger/base_library_temp", "dist/modmerger/base_library.zip")

shutil.copyfile("src/original.gdcc", "dist/modmerger/original.gdcc")
shutil.copyfile("README.md", "dist/README.md")
os.mkdir("dist/mods")
os.mkdir("dist/output")

shutil.make_archive("thehunter-mod-merger-win%i-%s" % (BITS, version.VERSION), "zip", root_dir="dist")

shutil.rmtree("dist")
shutil.rmtree("build")
os.remove("modmerger.spec")
