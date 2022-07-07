# thehunter-mod-merger

A simple, quick-and-dirty application for merging mods for theHunter: Call of the Wild. Note that this tool ONLY applies to mods that after the Revontuli update need to modify files in the global.gdcc.

This tool is capable of merging multiple .bin and global.gdcc-files as long as they don't have conflicts (that is, they modify the same parts of the file). This means that for example, you can have multiple mods that all modify global_simulation.bin, but as long as they all only modifiy different parts of that file they can still be merged.

## How to use

Download the mods you want and place them in the mods-folder in the application .exe directory. Note that each mod that is not a single global.gdcc should have a dropzone-named directory somewhere in their directory structure. This is because the part after that is used as a "virtual" directory path which will point inside an entry in global.gdcc. If you mess this up, you notice that the mod files are shown in the unknown files section.

If there are any conflicts (items shown as red), you must remove one of the conflicting mods before merging. Open the red tree item to see which file it conflicts with. Not much that can be done about this other than removing a mod causing the issue, although if you know some hex-editing you can always manually decide what to keep.

If everyting is OK, pressing the "Merge Mods" button should produce a merged global.gdcc in the output-directory. You can copy this file to your game dropzone. 

Also remember to set up your game launch options (including that last dot!):

`--vfs-fs dropzone --vfs-archive archives_win64 --vfs-fs.`

 In Steam, this is in Properties > General > Launch Options:
