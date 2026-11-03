LUT Converter 1.0
=================
Turns .cube LUT files (from DaVinci Resolve, Photoshop, Envato packs, etc.)
into PNG LUT textures for game engines.


HOW TO USE
----------
1. Open "LUT Converter.exe".
2. Drag .cube files (or a whole folder of them) onto the window.
3. Under "Export for", pick your engine.
4. Click "Export PNG", or "Export all to folder" to convert the whole list.

Tips
- "On image" shows the LUT on a color chart with a before/after slider.
  Drag one of your own screenshots onto the window to preview the LUT on it.
- "Strength" blends the LUT with the original colors (100% = full LUT).
  Double-click the slider to reset it.
- Right-click a LUT in the list for more options.


USING THE TEXTURE IN YOUR ENGINE
--------------------------------
Unreal Engine (256 x 16)
  - Import the PNG.
  - In the texture settings: Mip Gen Settings = NoMipmaps,
    Texture Group = ColorLookupTable.
  - In a Post Process Volume: Color Grading > Misc > Color Grading LUT.

Unity (1024 x 32)
  - Import the PNG. Turn off Generate Mip Maps, set Wrap Mode to Clamp
    and Compression to None.
  - In a Volume, add a Color Lookup override and assign the texture.


KEYBOARD SHORTCUTS
------------------
Ctrl+O          Add LUTs
Ctrl+S          Export the selected LUT
Ctrl+Shift+S    Export all
Ctrl+C          Copy the texture to the clipboard
Ctrl+Tab        Switch between Texture and On image
Delete          Remove the selected LUTs from the list


WINDOWS SAYS "WINDOWS PROTECTED YOUR PC"
----------------------------------------
That appears for any app that isn't signed with a paid certificate.
Click "More info", then "Run anyway".


SOMETHING WENT WRONG?
---------------------
Error details are saved to:  %LOCALAPPDATA%\LUT Converter\error.log
(Also reachable from the "..." menu > "Open error log folder".)
