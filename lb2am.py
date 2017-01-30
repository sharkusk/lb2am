# lb2am.py - https://github.com/sharkusk/lb2am
# Copyright (C) 2017 - Marcus Kellerman
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import xml.etree.ElementTree as ET
import argparse
import os
import glob
import shutil
import codecs

parser = argparse.ArgumentParser()
parser.add_argument('Launchbox_dir', help="Base Directory of Launchbox")
parser.add_argument('AttractMode_dir', help="Base Directory of AttractMode")
parser.add_argument('--genroms', action="store_true", help="Generate AttractMode romlists from Launchbox data.")
parser.add_argument('--genplats', action="store_true", help="Generate AttractMode platforms from Launchbox data.")
parser.add_argument('--renart', action="store_true", help="Rename artwork in Launchbox to be compatible with AttractMode.  Only the first image for each game in each directory will be renamed.")
parser.add_argument('--mergeart', action="store_true", help="Move missing artwork from AttractMode's scraper directory to Launchbox directories.")
parser.add_argument('--dryrun', action="store_true", help="Don't modify or create any files, only print operations that will be performed.")
parser.add_argument('--verbose', action="store_true", help="Dump the romlist and platform files to the console.")
parser.add_argument('--rlauncher', default='', help="Specify RocketLauncher executable, emulators are generated using RocketLauncher settings.")
parser.add_argument('-e', '--romext', default='.smc;.zip;.7z;.nes;.gba;.gb;.rom;.a26;.lnx;.gg;.int;.sms;.nds;.pce;.cue;.pbp;.iso;.cso;.32x;.bin;.rar;.dsk;.mx2;.lha;.n64;.wud;.wux;.rpx;.cdi;.adf;.d64;.t64',
        help="Override default rom extention (separated by ';')")
# TODO Create platform specific rom extensions
# TODO Specify single platform
# TODO Pick absolute or relative paths to be used
# TODO Overwrite, update or skip if file exists

args = parser.parse_args()

EmulatorName = ''

AM_HEADER = "#Name;Title;Emulator;CloneOf;Year;Manufacturer;Category;Players;Rotation;Control;Status;DisplayCount;DisplayType;AltRomname;AltTitle;Extra;Buttons"
AM_FIELD_MAP = [
    { "LB_Field": "ApplicationPath",    "AM_Field": "Name",         "MapToAm": (lambda aPath: os.path.splitext(os.path.split(aPath)[1])[0]) },
    { "LB_Field": "Title",              "AM_Field": "Title",        "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "Emulator",     "MapToAm": (lambda ignored: EmulatorName) },
    { "LB_Field": None,                 "AM_Field": "CloneOf",      "MapToAm": None },
    { "LB_Field": "ReleaseDate",        "AM_Field": "Year",         "MapToAm": (lambda ReleaseDate: ReleaseDate[:4]) },
    { "LB_Field": "Publisher",          "AM_Field": "Manufacturer", "MapToAm": None },
    { "LB_Field": "Genre",              "AM_Field": "Category",     "MapToAm": (lambda Genre: Genre.replace(';',' / ')) },
    { "LB_Field": None,                 "AM_Field": "Players",      "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "Rotation",     "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "Control",      "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "Status",       "MapToAm": None },
    { "LB_Field": "PlayCount",          "AM_Field": "DisplayCount", "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "DisplayType",  "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "AltRomname",   "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "AltTitle",     "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "Extra",        "MapToAm": None },
    { "LB_Field": None,                 "AM_Field": "Buttons",      "MapToAm": None }, ]

def ConvertToAMRomlist( LBPlatformFilePath ):
    # import pdb; pdb.set_trace()

    output = ''

    tree = ET.parse(LBPlatformFilePath)
    root = tree.getroot()

    output += AM_HEADER
    output += '\n'

    # Step through each game on the LaunchBox platform file
    for game in root.iter('Game'):
        # Step through each field needed in the AttractMode emulator file
        for field in AM_FIELD_MAP:
            t = u''
            # Check if Launchbox has a field that maps to AttractMode
            if field["LB_Field"]:
                try:
                    t = game.find(field["LB_Field"]).text
                except:
                    pass
            # Modify the Launchbox text if necessary
            if field["MapToAm"]:
                try:
                    t = field["MapToAm"](t)
                except:
                    pass
            if t:
                output += t
            # Each entry in AttractMode is separated by a ;
            output += ';'
        # We are all done with this entry
        output += '\n'

    # Sort the romlist
    output = '\n'.join(sorted(output.strip().split('\n')))

    return output

def CreateRomlists( LaunchboxBaseDir, AttractModeBaseDir ):
    platformsdir = os.path.join(LaunchboxBaseDir, 'Data', 'Platforms')
    romlistsdir = os.path.join(AttractModeBaseDir, 'romlists')

    # LB stores roms in individual xml files named after the platform
    files = glob.glob(os.path.join(platformsdir,"*.xml"))
    for file in files:
        print("Extracting ROMS from: "+file)
        # We use EmulatorName in a lamba, which needs to be global
        global EmulatorName
        EmulatorName = os.path.splitext(os.path.split(file)[1])[0] # Use platform filename as emulator name
        # LB may use unicode characters, so encode accordingly
        romListFileName = os.path.join(romlistsdir,EmulatorName+'.txt')
        output = ConvertToAMRomlist(file)
        if args.dryrun or args.verbose:
            print( ("Creating romlist: "+romListFileName).encode('utf-8') )
            if args.verbose:
                print( output.encode('utf-8') )
                print('')
        else:
            with codecs.open( romListFileName, 'w', 'utf-8') as fout:
                fout.write(output)
                fout.close()

ATTRACTMODE_EMULATOR_FILE_FORMAT = """#
# Generated by lb2am.py - https://github.com/sharkusk/lb2am
#
executable           %(appPath)s
args                 %(commandLine)s
rompath              %(romPath)s
romext               %(romExt)s
system               %(platformName)s
info_source          thegamesdb.net
%(artwork)s
"""

AM_IMAGES = {
        "artwork flyer     ": [ os.path.join("Images","%(platformName)s","Box - Front"),
                                os.path.join("Images","%(platformName)s","Advertisement Flyer - Front"),
                                os.path.join("Images","%(platformName)s","Box - 3D"),
                                os.path.join("Images","%(platformName)s","Arcade - Cabinet"), ],
        "artwork marquee   ": [ os.path.join("Images","%(platformName)s","Banner"),
                                os.path.join("Images","%(platformName)s","Arcade - Marquee"), ],
        "artwork snap      ": [ os.path.join("Images","%(platformName)s","Screenshot - Gameplay"),
                                os.path.join("Images","%(platformName)s","Screenshot - Game Title"),
                                os.path.join("Images","%(platformName)s","Screenshot - Game Select"),
                                os.path.join("Videos","%(platformName)s"), ],
        "artwork wheel     ": [ os.path.join("Images","%(platformName)s","Clear Logo"), ],
        "artwork fanart    ": [ os.path.join("Images","%(platformName)s","Fanart - Background"), ],
}

AM_IMAGE_REGIONS = [ "United States", "North America", "Europe", "Japan", ]

def CreateAmEmulators( LaunchboxBaseDir, AttractModeBaseDir ):
    tree = ET.parse(os.path.join(LaunchboxBaseDir, 'Data', 'Emulators.xml'))
    root = tree.getroot()

    # Emulators and platforms are separated in LB, they are cross referenced through a unique ID
    EM_FIELDS = [ 'Title', 'ApplicationPath', 'CommandLine', 'NoSpace', 'NoQuotes', ]
    emulatordict = {}

    # Create a dictionary of emulator information we can use when parsing the
    # LB emulator platforms.  Format is as follows:
    # { ID: { "Title": title, "ApplicationPath": path, "CommandLine": cmdline } }
    for emulator in root.findall('Emulator'):
        emulatorEntry = {}
        for field in EM_FIELDS:
            emulatorEntry[field] = emulator.find(field).text
        emulatordict[emulator.find('ID').text] = emulatorEntry

    # Now we can parse each emulator platform and combine with the information
    # stored in the dictionary above to create an AM emulator
    for emulatorPlatform in root.findall('EmulatorPlatform'):
        if emulatorPlatform.find('Default').text == 'true':
            platformName = emulatorPlatform.find('Platform').text
            print("Creating Emulator: "+platformName)

            if args.rlauncher:
                appPath = os.path.abspath(args.rlauncher)
                commandLine = 'args -s "[emulator]" -r "[name]" -p AttractMode -f "%s"' % os.path.join(os.path.abspath(AttractModeBaseDir), 'attract.exe')
                romPath = ''
            else:
                # Launchbox stores the rom path for each rom, while Attractmode uses
                # a list of rompaths for each emulator
                romPath = []
                try:
                    plattree = ET.parse(os.path.join(LaunchboxBaseDir, 'Data', 'Platforms', platformName+'.xml'))
                    platroot = plattree.getroot()
                    for game in platroot.findall('Game'):
                        romPath.append(os.path.abspath(os.path.split(game.find('ApplicationPath').text)[0]))
                except:
                    pass

                # Remove duplicates and convert to string
                romPath = list(set(romPath))
                romPath = ';'.join(romPath)

                # Lookup the application path for this emulator (using our dictionary)
                appPath = emulatordict[emulatorPlatform.find('Emulator').text]['ApplicationPath']
                appPath = os.path.abspath(os.path.join(LaunchboxBaseDir, appPath))
                commandLine = emulatorPlatform.find('CommandLine').text
                if not commandLine:
                    commandLine = ''
                # TODO Map other front-end commandline options between LB and AM
                if emulatordict[emulatorPlatform.find('Emulator').text]['NoSpace'] == 'false':
                    commandLine += ' '
                if emulatordict[emulatorPlatform.find('Emulator').text]['NoQuotes'] == 'true':
                    commandLine += '[romfilename]'
                else:
                    commandLine += '"[romfilename]"'
            romExt = args.romext

            artworkText = ''
            for artPrefix in AM_IMAGES.keys():
                artworkText += artPrefix
                for artDirNames in AM_IMAGES[artPrefix]:
                    artDirNames = artDirNames % { 'platformName': platformName }
                    artworkText += os.path.join(os.path.abspath(LaunchboxBaseDir), artDirNames)+';'
                    for region in AM_IMAGE_REGIONS:
                        artworkText += os.path.join(os.path.abspath(LaunchboxBaseDir), artDirNames, region)+';'
                artworkText += '\n'

            output = ATTRACTMODE_EMULATOR_FILE_FORMAT % { "appPath": appPath, "commandLine": commandLine, "romPath": romPath, "romExt": romExt, "platformName": platformName, "artwork": artworkText }

            # Attractmode uses Unix style paths, so replace the windows \'s
            output = output.replace('\\', '/').strip()

            platformFileName = os.path.join(AttractModeBaseDir,'emulators',platformName+'.cfg')

            if args.dryrun or args.verbose:
                print( ("Writing emulator file: "+platformFileName).encode('utf-8') )
                if args.verbose:
                    print( output.encode('utf-8') )
                    print('')
            else:
                with codecs.open( platformFileName, 'w', 'utf-8') as fout:
                    fout.write(output)
                    fout.close()

def RenameLBArtwork( LaunchboxBaseDir, AttractModeBaseDir ):
    romlistsdir = os.path.join(AttractModeBaseDir, 'romlists')

    files = glob.glob(os.path.join(romlistsdir,"*.txt"))
    for romListFileName in files:
        platformName = os.path.splitext(os.path.split(romListFileName)[1])[0]
        print("Renaming artwork for: " + platformName)

        # Create list of platform specific artwork directories
        artDirs = []
        for key in AM_IMAGES.keys():
            for value in AM_IMAGES[key]:
                # Insert platform name into each entry
                value = value % { 'platformName': platformName }
                artDirs.append(os.path.join(os.path.abspath(LaunchboxBaseDir), value))
                # LB also stores images in specific region specific folders
                for region in AM_IMAGE_REGIONS:
                    artDirs.append(os.path.join(os.path.abspath(LaunchboxBaseDir), value, region))

        plattree = ET.parse(os.path.join(LaunchboxBaseDir, 'Data', 'Platforms', platformName+'.xml'))
        platroot = plattree.getroot()
        for game in platroot.findall('Game'):
            # LB uses the game title (not filename) for images when scraping.
            # We need to rename these files to match the rom filename for AM
            gameFileName = os.path.splitext(os.path.split(game.find('ApplicationPath').text)[1])[0]
            gameName = game.find('Title').text

            # When LB saves image files, it replaces the following chacters with '_'
            LB_FILE_SUB = [ ':', "'", '\\', '/', '"', '?', '<', '>', '!', '|' ]

            for sub in LB_FILE_SUB:
                gameName = gameName.replace( sub, '_' )

            images = []
            for artDir in artDirs:
                searchString = os.path.join(artDir,gameName+'-01.*')
                images.extend(glob.glob(searchString))

            for image in images:
                # First, extract the extension
                ext = os.path.splitext(image)[1]
                # Remove the old filename (keep the path), then append the new filename and old extension
                newImage = os.path.join(os.path.split(image)[0],gameFileName+ext)
                if args.dryrun:
                    print( ("Renaming "+image+" to "+newImage).encode('utf-8') )
                else:
                    os.rename(image,newImage)

AM_TO_LB_ART_PATH = [
        ( os.path.join("scraper","%(platformName)s","flyer"),   os.path.join("Images","%(platformName)s","Box - Front") ),
        ( os.path.join("scraper","%(platformName)s","marquee"), os.path.join("Images","%(platformName)s","Banner") ),
        ( os.path.join("scraper","%(platformName)s","wheel"),   os.path.join("Images","%(platformName)s","Clear Logo") ),
        ( os.path.join("scraper","%(platformName)s","fanart"),  os.path.join("Images","%(platformName)s","Fanart - Background") ),
    ]
def MergeArtworkToLB( LaunchboxBaseDir, AttractModeBaseDir ):
    # import pdb; pdb.set_trace()
    # Get list of directories in AM's scraper directory
    amScraperPlats = next(os.walk(os.path.join(AttractModeBaseDir, 'scraper')))[1]
    for platformName in amScraperPlats:
        for artPath in AM_TO_LB_ART_PATH:
            searchString = os.path.join(AttractModeBaseDir, artPath[0] % { "platformName": platformName }, '*')
            imagesToMove = glob.glob(searchString)
            for image in imagesToMove:
                # Get the filename and add it to the LB art path
                newPath = os.path.join(LaunchboxBaseDir, artPath[1] % { "platformName": platformName }, os.path.split(image)[1])
                # Next, see if it exists in LB
                if os.path.isfile( newPath ):
                    # File already exists, so we can move to the next one
                    continue
                if args.dryrun:
                    print( ("Moving "+image+" to "+newPath).encode('utf-8') )
                else:
                    shutil.move(image, newPath)

if args.genroms:
    CreateRomlists( args.Launchbox_dir, args.AttractMode_dir )
if args.genplats:
    CreateAmEmulators( args.Launchbox_dir, args.AttractMode_dir )
if args.renart:
    RenameLBArtwork( args.Launchbox_dir, args.AttractMode_dir )
if args.mergeart:
    MergeArtworkToLB( args.Launchbox_dir, args.AttractMode_dir )
