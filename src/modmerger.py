
import sys
import os
import hashlib

from tkinter import *
from tkinter import messagebox
from tkinter.ttk import *

from intervaltree import Interval, IntervalTree

from deca import ff_file, ff_adf
import version

APP_PATH = os.path.dirname(os.path.realpath(__file__))

GLOBAL_GDCC = "global.gdcc"
ORIGINAL_GDCC = os.path.join(APP_PATH, "original.gdcc")
MOD_DIR = os.path.abspath(os.path.join(APP_PATH, "../mods"))
OUTPUT_DIR = os.path.abspath(os.path.join(APP_PATH, "../output"))

print("Starting Mod Merger...")
print("App Path: %s" % APP_PATH)
print("Mod directory: %s" % MOD_DIR)
print("Output directory: %s" % OUTPUT_DIR)

KNOWN_GDCC_HASHES = [
    "59baa86577fbcbeeb5b401738b1a9c04", #Revontuli update (28 June 2022)
]

PAD = 5
UNKNOWN_TEXT = "Unknown files not listed in global.gdcc. These will not be merged and can be ignored."
ORIGINAL_MISSING = 'You must place an UNMODIFIED "%s" in the app directory.' % ORIGINAL_GDCC

HASH_WARNING = """\
The content hash of "%s" does not match any known files.

This is probably fine, but make sure the files and this program is up-to-date.""" % (ORIGINAL_GDCC)

MERGE_OK = """\
Merged file was written to "%s".

You can now copy this file to "..../theHunterCotW/dropzone/gdc/global.gdcc".

Remember to also set the game launch options if you haven't already!"""

FORCE_MERGE = """\
!!! WARNING - THERE ARE MOD CONFLICTS !!!

This operation will forcefully merge all mods. When resolving conflicts, a file listed higher in \
the view listing will win. If you want to change this order, simply rename or create a directory with another name, \
they are sorted alphabetically (using their full path).

The results of a forced merge may or may not work, depending on how the mods have modified the files. \
The game may also crash or become unstable.

Are you sure you want to force the merge?"""

MERGE_STATE_OK = 1
MERGE_STATE_CONFLICTS = 2
MERGE_STATE_ERROR = 3

class ModFile:
    def __init__(self, name, file_path, gdcc_path):
        self.name = name
        self.file_path = file_path
        self.gdcc_path = gdcc_path

def sort_mod_files(files):
    return sorted(files, key=lambda f: f.file_path.lower())

class ModMergerApp(Tk):
    def __init__(self):
        super().__init__()

        self.frame = Frame(self)
        self.frame.pack(expand=True, fill=BOTH, padx=PAD, pady=PAD)

        self.create_views(self.frame)

        self.after(1, self.merge_mods)

    def merge_mods(self):
        if not os.path.isfile(ORIGINAL_GDCC):
            messagebox.showerror("Error", ORIGINAL_MISSING)
            sys.exit()

        self.adf = self.read_global_gdcc()
        self.file_paths, self.interval_tree = self.get_gdcc_files()
        self.mod_files, self.unknown_files = self.find_mod_files()

        original_gdcc = open(ORIGINAL_GDCC, "rb").read()
        gdcc_hash = hashlib.md5(original_gdcc).hexdigest()
        self.merged_gdcc = bytearray(original_gdcc)

        overwritten = {}
        self.file_info = {}
        self.file_info.update(self.merge_gdccs(original_gdcc, self.merged_gdcc, overwritten))
        self.file_info.update(self.merge_files(original_gdcc, self.merged_gdcc, overwritten))

        self.merge_state = MERGE_STATE_OK
        for item in self.file_info.values():
            if item["error"]:
                #Serious error, bail out.
                self.merge_state = MERGE_STATE_ERROR
                break
            elif item["conflicts"]:
                self.merge_state = MERGE_STATE_CONFLICTS

        self.update_tree_view()

        if gdcc_hash not in KNOWN_GDCC_HASHES:
            messagebox.showwarning("%s Warning" % ORIGINAL_GDCC, HASH_WARNING)

        button_state = NORMAL if len(self.mod_files) > 0 else DISABLED
        self.merge_button.configure(state=button_state)

        force_state = NORMAL if len(self.mod_files) > 0 and self.merge_state == MERGE_STATE_CONFLICTS else DISABLED
        self.force_button.configure(state=force_state)

    def read_global_gdcc(self):
        with open(ORIGINAL_GDCC, "rb") as f:
            archive = ff_file.ArchiveFile(f)
            adf = ff_adf.Adf()
            adf.deserialize(archive)
        return adf

    def get_gdcc_files(self):
        files = {}
        interval_tree = IntervalTree()
        for i, instance in enumerate(self.adf.table_instance_values):
            for item in instance:
                path = str(item.v_path, "ascii")
                if path in files:
                    raise Exception("Duplicate file %s" % path)
                item._file_offset = self.adf.table_instance[i].offset
                files[path] = item

                global_offset = item._file_offset + item.offset
                interval_tree[global_offset:global_offset+item.size] = path

        return files, interval_tree

    def find_mod_files(self):
        mod_files = []
        unknown = []
        for root, dirs, files in os.walk(MOD_DIR):
            for name in files:
                file_path = os.path.join(root, name).replace("\\", "/")
                gdcc_path = file_path.split("dropzone/")[-1]

                if name == GLOBAL_GDCC or gdcc_path in self.file_paths:
                    mod_files.append(ModFile(name, file_path, gdcc_path))
                else:
                    unknown.append(ModFile(name, file_path, ""))

        return sort_mod_files(mod_files), sort_mod_files(unknown)

    def merge_gdccs(self, original_gdcc, write_gdcc, overwritten):
        gdccs = [f for f in self.mod_files if f.name == GLOBAL_GDCC]
        contents = [open(p.file_path, "rb").read() for p in gdccs]

        infos = {}
        for i, gd in enumerate(gdccs):
            error = ""
            file_size = len(contents[i])
            if file_size != len(original_gdcc):
                error = "File size does not match, should be %i" % len(original_gdcc)

            infos[gd.file_path] = {
                "changed": 0,
                "conflicts": set(),
                "file_size": file_size,
                "error": error,
                "files_changed": set(),
            }

        for i, original_byte in enumerate(original_gdcc):
            for x, gdcc in enumerate(gdccs):
                gdcc_data = contents[x]

                try:
                    gdcc_byte = gdcc_data[i]
                    self.compare_byte(gdcc, i, gdcc_byte, original_byte,
                        original_gdcc, write_gdcc, overwritten, infos)
                except IndexError:
                    #Probably wrong file size
                    if not infos[gdcc.file_path]["error"]:
                        infos[gdcc.file_path]["error"] = "Invalid index at %i" % i

        return infos

    def compare_byte(self, mod_file, i, file_byte, original_byte, original_gdcc, write_gdcc, overwritten, infos):
        original_changed = (file_byte != original_gdcc[i])
        if original_changed:
            infos[mod_file.file_path]["changed"] += 1

            for p in self.interval_tree[i]:
                infos[mod_file.file_path]["files_changed"].add(p.data)

        changed = original_changed and (file_byte != write_gdcc[i])
        if changed:
            #print(mod_file.file_path, i)

            if i in overwritten:
                #Byte has been changed and is not the same as our change.
                infos[mod_file.file_path]["conflicts"].add(overwritten[i])
            else:
                write_gdcc[i] = file_byte
                overwritten[i] = mod_file.file_path

    def merge_files(self, original_gdcc, write_gdcc, overwritten):
        file_groups = {}
        for mod_file in [f for f in self.mod_files if f.name != GLOBAL_GDCC]:
            if mod_file.gdcc_path in file_groups:
                file_groups[mod_file.gdcc_path].append(mod_file)
            else:
                file_groups[mod_file.gdcc_path] = [mod_file]

        infos = {}
        for path_group in file_groups.values():
            for mod_file in sort_mod_files(path_group):
                entry = self.file_paths[mod_file.gdcc_path]
                raw = open(mod_file.file_path, "rb").read()

                error = ""
                if len(raw) != entry.size:
                    error = "File size does not match global.gdcc entry size, should be %i" % entry.size

                info = {
                    "changed": 0,
                    "conflicts": set(),
                    "file_size": len(raw),
                    "error": error,
                    "files_changed": set(),
                }
                infos[mod_file.file_path] = info

                file_offset = entry.offset + entry._file_offset
                for i in range(0, entry.size):
                    index = file_offset + i

                    try:
                        original_byte = original_gdcc[index]
                        file_byte = raw[i]
                        self.compare_byte(mod_file, index, file_byte, original_byte,
                            original_gdcc, write_gdcc, overwritten, infos)
                    except IndexError:
                        #Probably wrong file size
                        if not info["error"]:
                            info["error"] = "Invalid index at %i" % i

        return infos

    def create_views(self, root):
        columns = ("type", "size", )
        tree = Treeview(root, columns=columns)

        tree.heading('#0', text="File name", anchor="w")

        tree.heading('type', text='Bytes changed', anchor="w")
        tree.column("type", anchor="w", width=100, stretch=0)

        tree.heading('size', text='File Size', anchor="w")
        tree.column("size", anchor="w", width=100, stretch=0)

        def item_selected(event):
            pass

        tree.bind('<<TreeviewSelect>>', item_selected)
        tree.grid(row=0, column=0, sticky='nsew')

        scrollbar = Scrollbar(root, orient=VERTICAL, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        tree.configure(yscroll=scrollbar.set)

        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)

        button_frame = Frame(root)
        button_frame.grid(row=1, column=0, padx=PAD, pady=PAD)

        self.merge_button = Button(button_frame, text="Merge Mods", command=self.merge_pressed, width=20)
        self.merge_button.pack(side=LEFT)

        self.force_button = Button(button_frame, text="Force Merge", command=self.merge_force_pressed, width=20)
        self.force_button.pack(side=LEFT, padx=PAD)

        self.refresh_button = Button(button_frame, text="Refresh", command=self.refresh_pressed, width=20)
        self.refresh_button.pack(side=LEFT)

        self.tree = tree

    def merge_force_pressed(self):
        if messagebox.askyesno("Force Merge", FORCE_MERGE):
            self.save_merged(True)

    def merge_pressed(self):
        self.save_merged(False)

    def save_merged(self, force):
        out_path = os.path.join(OUTPUT_DIR, GLOBAL_GDCC).replace("\\", "/")
        try:
            os.remove(out_path)
        except OSError:
            pass

        if not force:
            if self.merge_state != MERGE_STATE_OK:
                messagebox.showerror("Merge Failed!", "Remove any errors and conflicts before trying to merge.")
                return

        if not os.path.exists(OUTPUT_DIR):
            os.mkdir(OUTPUT_DIR)

        with open(out_path, "wb") as out:
            out.write(self.merged_gdcc)

        messagebox.showinfo("Merge Successful!", MERGE_OK % out_path)

    def refresh_pressed(self):
        self.clear_tree()
        self.after(1, self.merge_mods)

    def clear_tree(self):
        self.tree.delete(*self.tree.get_children())

    def trim_path(self, path):
        mods_path = MOD_DIR.replace("\\", "/") + "/"
        path = path.replace("\\", "/")
        if path.startswith(mods_path):
            path = path.replace(mods_path, "", 1)
        return path

    def update_tree_view(self):
        self.clear_tree()

        if not self.mod_files and not self.unknown_files:
            self.tree.insert("", END, text="No files found. Place them inside the '%s' directory." % MOD_DIR)
            return

        if self.unknown_files:
            self.tree.insert("", END, iid="unknown", text=UNKNOWN_TEXT, open=False)
            for f in self.unknown_files:
                self.tree.insert("unknown", END, text=self.trim_path(f.file_path))

        self.tree.insert("", END, iid="root", text="Modded files", open=True)

        for f in self.mod_files:
            info = self.file_info.get(f.file_path)
            changed = ""
            size = ""
            error = ""
            color = "green_fg"
            if info:
                changed = str(info["changed"])
                size = str(info["file_size"])
                error = info.get("error")
                if info["conflicts"] or error:
                    color = "red_fg"

            iid = self.tree.insert("root", END, text=self.trim_path(f.file_path), values=(changed, size), tags=[color])

            if error:
                self.tree.insert(iid, END, text="Error: %s" % error, tags=["red_fg"])

            if info:
                for clash in info["conflicts"]:
                    self.tree.insert(iid, END, text="Conflicts with: %s" % self.trim_path(clash), tags=["red_fg"])

                if info["files_changed"]:
                    changed_iid = self.tree.insert(iid, END, text="Changed files in global.gdcc", tags=[color], open=True)
                    for c in sorted(info["files_changed"]):
                        self.tree.insert(changed_iid, END, text=c, tags=[color])

        self.tree.tag_configure("green_fg", foreground="green")
        self.tree.tag_configure("red_fg", foreground="red")

app = ModMergerApp()
app.title("theHunter COTW Mod Merger (%s)" % version.VERSION)
app.geometry("1024x600")
app.mainloop()
