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
parser.add_argument('-r', '--rlauncher', default='', help="Specify RocketLauncher executable, emulators are generated using RocketLauncher settings.")
parser.add_argument('-e', '--romext', default='.smc;.zip;.7z;.nes;.gba;.gb;.rom;.a26;.lnx;.gg;.int;.sms;.nds;.pce;.cue;.pbp;.iso;.cso;.32x;.bin;.rar;.dsk;.mx2;.lha;.n64;.wud;.wux;.rpx;.cdi;.adf;.d64;.t64', help="Override default rom extention (separated by ';')")
# TODO Specify single platform
# TODO Specify romlist or emulator import
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
            # Special case the emulator AttractMode field
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
                # print(t.encode('utf-8')),
                output += t
            # Each entry in the AttractMode is separated by a ;
            output += ';'
            # print(';'),
        # We are all done with this entry
        output += '\n'
        # print('')

    # Sort the romlist
    output = '\n'.join(sorted(output.split('\n')))

    # print output.encode('utf-8')
    return output

def CreateRomlists( LaunchboxBaseDir, AttractModeBaseDir ):
    platformsdir = os.path.join(LaunchboxBaseDir, 'Data', 'Platforms')
    romlistsdir = os.path.join(AttractModeBaseDir, 'romlists')

    files = glob.glob(os.path.join(platformsdir,"*.xml"))
    for file in files:
        print("Creating RomList for: "+file)
        global EmulatorName
        EmulatorName = os.path.splitext(os.path.split(file)[1])[0] # Use platform filename as emulator name
        with codecs.open(os.path.join(romlistsdir,EmulatorName+'.txt'), 'w', 'utf-8') as fout:
            fout.write(ConvertToAMRomlist(file))
            fout.close()

ATTRACTMODE_EMULATOR_FILE_FORMAT = """#
# Generated by lb2am.py
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
        "artwork flyer     ": [ "Images/%(platformName)s/Box - Front", "Images/%(platformName)s/Advertisement Flyer - Front", "Images/%(platformName)s/Box - 3D", "Images/%(platformName)s/Arcade - Cabinet", ],
        "artwork marquee   ": [ "Images/%(platformName)s/Banner", "Images/%(platformName)s/Arcade - Marquee", ],
        "artwork snap      ": [ "Images/%(platformName)s/Screenshot - Gameplay", "Images/%(platformName)s/Screenshot - Game Title", "Images/%(platformName)s/Screenshot - Game Select", "Videos/%(platformName)s", ],
        "artwork wheel     ": [ "Images/%(platformName)s/Clear Logo", ],
}

AM_IMAGE_REGIONS = [ "Europe", "Japan", "North America", "United States", ]

def CreateAmEmulators( LaunchboxBaseDir, AttractModeBaseDir ):
    tree = ET.parse(os.path.join(LaunchboxBaseDir, 'Data', 'Emulators.xml'))
    root = tree.getroot()

    # Emulators and platforms are separated in LB, they are cross referenced through a unique ID
    EM_FIELDS = [ 'Title', 'ApplicationPath', 'CommandLine', 'NoSpace', ]
    emulatordict = {} # { ID: { "Title": title, "ApplicationPath": path, "CommandLine": cmdline } }
    for emulator in root.findall('Emulator'):
        emulatorEntry = {}
        for field in EM_FIELDS:
            emulatorEntry[field] = emulator.find(field).text
        emulatordict[emulator.find('ID').text] = emulatorEntry


    for emulatorPlatform in root.findall('EmulatorPlatform'):
        if emulatorPlatform.find('Default').text == 'true':
            platformName = emulatorPlatform.find('Platform').text
            print("Creating Emulator: "+platformName)
            if args.rlauncher:
                appPath = os.path.abspath(args.rlauncher)
                commandLine = 'args -s "[emulator]" -r "[name]" -p AttractMode -f "%s"' % os.path.join(os.path.abspath(AttractModeBaseDir), 'attract.exe')
            else:
                appPath = emulatordict[emulatorPlatform.find('Emulator').text]['ApplicationPath']
                appPath = os.path.abspath(os.path.join(LaunchboxBaseDir, appPath))
                commandLine = emulatorPlatform.find('CommandLine').text
                if not commandLine:
                    commandLine = ''
                # TODO Map front-end commandline options between LB and AM
                if emulatordict[emulatorPlatform.find('Emulator').text]['NoSpace'] == 'false': 
                    commandLine += ' '
                commandLine += '[romfilename]'
            # TODO Use Platforms.xml to obtain default ROM path
            romPath = '.'
            romExt = args.romext

            artwork = ''
            for k in AM_IMAGES.keys():
                artwork += k
                for d in AM_IMAGES[k]:
                    d = d % { 'platformName': platformName }
                    artwork += os.path.join(os.path.abspath(LaunchboxBaseDir), d)+';'
                    for region in AM_IMAGE_REGIONS:
                        artwork += os.path.join(os.path.abspath(LaunchboxBaseDir), d, region)+';'
                artwork += '\n'

            # import pdb; pdb.set_trace()
            output = ATTRACTMODE_EMULATOR_FILE_FORMAT % { "appPath": appPath, "commandLine": commandLine, "romPath": romPath, "romExt": romExt, "platformName": platformName, "artwork": artwork }

            # Attractmode uses Unix style paths, so replace the \'s
            output = output.replace('\\', '/')

            with codecs.open(os.path.join(AttractModeBaseDir,'emulators',platformName+'.cfg'), 'w', 'utf-8') as fout:
                fout.write(output)
                fout.close()

def RenameLBArtwork( LaunchboxBaseDir, AttractModeBaseDir ):
    romlistsdir = os.path.join(AttractModeBaseDir, 'romlists')

    files = glob.glob(os.path.join(romlistsdir,"*.txt"))
    for f in files:
        platformName = os.path.splitext(os.path.split(f)[1])[0]
        print("Renaming artwork for: " + platformName)

        artDirs = []
        for key in AM_IMAGES.keys():
            for value in AM_IMAGES[key]:
                value = value % { 'platformName': platformName }
                artDirs.append(os.path.join(os.path.abspath(LaunchboxBaseDir), value))
                for region in AM_IMAGE_REGIONS:
                    artDirs.append(os.path.join(os.path.abspath(LaunchboxBaseDir), value, region))

        file = open(f)
        for line in file:
            if line.lstrip()[0] == '#':
                continue
            try:
                gameFileName, gameName, __ = line.split(';', 2)
            except:
                continue

            images = []
            for artDir in artDirs:
                searchString = os.path.join(artDir,gameName+'-01.*')
                images.extend(glob.glob(searchString))

            for image in images:
                __, ext = os.path.splitext(image)
                newImage = os.path.join(os.path.split(image)[0],gameFileName+ext)
                # print( "Renaming "+image+" to "+newImage )
                os.rename(image,newImage)

if args.genroms:
    CreateRomlists( args.Launchbox_dir, args.AttractMode_dir )
if args.genplats:
    CreateAmEmulators( args.Launchbox_dir, args.AttractMode_dir )
if args.renart:
    RenameLBArtwork( args.Launchbox_dir, args.AttractMode_dir )
