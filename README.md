# LB2AM

This tool imports your LaunchBox configuration into AttractMode.  

Features includes:

* Generates AttractMode Romlists - Parses LB Platforms files, extracts ROM names, titles and other meta data and creates associated AttractMode rom lists for each platform
* Generates AttractMode Platforms - Parses LB Emulator file and creates associated platforms
* Optional RocketLauncher Based Platforms - Configures AttractMode to utilize RocketLauncher to load roms.
* Renames LaunchBox artwork - AttractMode looks for image files that matches the rom name.  LaunchBox also will look for this, but by default stores images using the rom's title and number.  This option renames the first image in each category to be compatible with AttractMode (while still working for LB)
* Merge AttractMode Artwork into LaunchBox - This consolidates all artwork into the LaunchBox directories

WARNING: This script will overwrite files in your AttractMode directory.

WARNING: This script will rename artwork files in your LaunchBox directory.

It is strongly suggested that you backup before running!  Use the '--dryrun' and '--verbose' options wisely!

```
usage: lb2am.py [-h] [--genroms] [--genplats] [--renart] [--mergeart]
                [--dryrun] [--verbose] [--rlauncher RLAUNCHER] [-e ROMEXT]
                Launchbox_dir AttractMode_dir

positional arguments:
  Launchbox_dir         Base Directory of Launchbox
  AttractMode_dir       Base Directory of AttractMode

optional arguments:
  -h, --help            show this help message and exit
  --genroms             Generate AttractMode romlists from Launchbox data.
  --genplats            Generate AttractMode platforms from Launchbox data.
  --renart              Rename artwork in Launchbox to be compatible with
                        AttractMode. Only the first image for each game in
                        each directory will be renamed.
  --mergeart            Move missing artwork from AttractMode's scraper
                        directory to Launchbox directories.
  --dryrun              Don't modify or create any files, only print
                        operations that will be performed.
  --verbose             Dump the romlist and platform files to the console.
  --rlauncher RLAUNCHER
                        Specify RocketLauncher executable, emulators are
                        generated using RocketLauncher settings.
  -e ROMEXT, --romext ROMEXT
                        Override default rom extention (separated by ';')
```
