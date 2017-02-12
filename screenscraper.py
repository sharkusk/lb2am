# -*- coding: utf-8 -*-
# screenscraper.py - https://github.com/sharkusk/lb2am
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
import os
import urllib2, urllib
import binascii
import zipfile
import zlib

SS_USER_INFO_CMD = "ssuserInfos"
SS_SYSTEMS_LIST_CMD = "systemesListe"
SS_GAME_INFO_CMD = "jeuInfos"
SS_GAME_INFO_PARMS = [ 'crc', 'md5', 'sha1', 'systemeid', 'romtype', 'romnom', 'romtaille', ]

class ScreenScraper(object):
    SS_BASE_URL = "https://www.screenscraper.fr/api/%s.php?"

    def __init__(self, devid, devpassword, softname, ssid, sspassword, verbose=False):
        self.parameters = {}
        self.parameters['devid'] = devid
        self.parameters['devpassword'] = devpassword
        self.parameters['softname'] = softname
        self.parameters['ssid'] = ssid
        self.parameters['sspassword'] = sspassword
        self.parameters['output'] = 'xml'
        self.verbose = verbose
        self.command = None
        self.cachedir = 'cache'

    def SendRequest(self):
        if not self.command:
            return

        requestUrl = self.SS_BASE_URL % self.command
        requestUrl += urllib.urlencode(self.parameters)

        if self.verbose:
            print(requestUrl)

        response = urllib2.urlopen(requestUrl)
        output = response.read()
        # Unicode characters are often received, so format accordingly
        output = unicode(output,'utf-8')
        if not output.startswith('<?xml version="1.0" encoding="UTF-8" ?>'):
            raise InvalidResponseError(requestUrl,output)

        return output

class UserInfo(ScreenScraper):
    """ This class is used to obtain user information. """
    USER_INFO = ['id', 'niveau', 'contribution', 'uploadsysteme', 'uploadinfos', 'romasso', 'uploadmedia', 'maxthreads', 'maxdownloadspeed', 'visites', 'datedernierevisite', 'favregion',]

    def __init__(self, devid, devpassword, softname, ssid, sspassword, verbose=False):
        super(UserInfo, self).__init__(devid, devpassword, softname, ssid, sspassword, verbose)
        self.command = SS_USER_INFO_CMD
        xml = self.SendRequest()
        self.root = ET.fromstring(xml.encode('utf-8'))
        if self.verbose:
            print("Created UserInfo class.")

    def GetUserInfo(self):
        if self.verbose:
            print("Getting user info for '%s'." % self.parameters['ssid'])

        userinfo = {}
        ssuser = self.root.find('ssuser')

        for item in self.USER_INFO:
            userinfo[item] = ssuser.find(item).text
            if self.verbose:
                print("%s: %s" % (item, userinfo[item]))

        return userinfo

SS_SYSTEM_XML_FILE = "screenscraper.fr-systemesListe.xml"

class SystemList(ScreenScraper):
    """ This class is used to obtain the system list and associated media. """
    def __init__(self, devid, devpassword, softname, ssid, sspassword, updateCache=False, verbose=False):
        super(SystemList, self).__init__(devid, devpassword, softname, ssid, sspassword, verbose)

        self.command = SS_SYSTEMS_LIST_CMD

        systemXmlFile = os.path.join( self.cachedir, SS_SYSTEM_XML_FILE )
        if updateCache or not os.path.isfile( systemXmlFile ):
            with open(systemXmlFile, 'w') as f:
                f.write(self.SendRequest().encode('utf-8'))
                f.close()

        self.root = ET.parse(systemXmlFile)
        if self.verbose:
            print("Created SystemList class.")

    def GetSystemList(self):
        """
        System list is a dictionary containing { "SystemName": "ScreenScaperId" }
        There may be multiple SystemNames with the same ScreenScraperId
        """
        if self.verbose:
            print("Getting system list.")

        systemList = {} 

        for system in self.root.iter('systeme'):
            try:
                companyName = system.find('compagnie').text
            except:
                companyName = ''
            for name in system.find('noms'):
                systemList[name.text] = system.find('id').text
                if self.verbose:
                    print("  %s: %s" % (systemList[name.text], name.text))
                # Create separate entries for company + name if company is not already
                # included in the system name
                if companyName and name.text.find(companyName) == -1:
                    systemList[companyName+' '+name.text] = system.find('id').text
                    if self.verbose:
                        print("  %s: %s" % (systemList[companyName+' '+name.text], companyName+' '+name.text))
        return systemList

    def __getSystem(self, systemid):
        for system in self.root.iter('systeme'):
            if system.find('id').text == systemid:
                return system
        else:
            return None

    def GetInfo(self, systemid):
        if self.verbose:
            print("Getting system info.")

        system = self.__getSystem(systemid)
        systeminfo = {}
        if system is None:
            return None

        for item in ['parentid','compagnie','type','datedebut','datefin','romtype','supporttype',]:
            try:
                systeminfo[item] = system.find(item).text
            except:
                continue
            if self.verbose:
                print("  %s: %s" % (item, systeminfo[item]))
        return systeminfo

    def GetAvailableMedia(self, systemid):
        """
        Media Dictionary looks like this:
          --mediaCategory--   --list of mediaEntries--
        { 'logosmonochrome': [{'url': 'http...', 'region': 'jp', 'crc': 'XYZ', 'md5': 'XXX', 'sha1': 'YYY'}, ...]},
        ...
        """
        if self.verbose:
            print("Getting system media for id %s." % systemid)

        system = self.__getSystem(systemid)
        if system is None:
            return None

        try:
            medias = system.find('medias')
        except:
            return availableMedia

        return get_media(medias, self.verbose)

def get_crc( romPath ):
    # Check if there is a separate CRC file that we should use
    if os.path.exists(romPath+'.crc'):
        with open(romPath+'.crc', 'r') as f:
            crc = f.read().strip()
            f.close()
            if not crc:
                print("    Empty CRC file detected: %s" % romPath+'.crc')
                crc = None 
            else:
                print("    Using CRC file: %s", romPath+'.crc')
            return crc
    else:
        # If this is a zipfile, get the gamename and crc from inside the zip
        if os.path.splitext(romPath)[1].lower() == '.zip':
            zf = zipfile.ZipFile(romPath, 'r')
            info = zf.infolist()
            # This only works if there is one file in the zip
            if len(info) == 1:
                print("    Using ZIP file CRC")
                return "%08X" % info[0].CRC
        return crc32_from_file(romPath)

class GameInfo(ScreenScraper):
    """ This class is used to obtain the game information and associated media. """
    def __init__(self, devid, devpassword, softname, ssid, sspassword, systemId, romPath=None, romName=None, crc=None, md5=None, sha1=None, romType=None, romSize=None, gameTitle=None, updateCache=False, verbose=False):
        super(GameInfo, self).__init__(devid, devpassword, softname, ssid, sspassword, verbose)

        # import pdb; pdb.set_trace()
        self.command = SS_GAME_INFO_CMD
        if md5 is not None:
            self.parameters['md5'] = md5
        if sha1 is not None:
            self.parameters['sha1'] = sha1
        if systemId is not None:
            self.parameters['systemeid'] = systemId
        if romType is not None:
            self.parameters['romtype'] = romType
        if romSize is not None:
            self.parameters['romtaille'] = romSize

        gameFileName = ''
        zipRomName = ''

        cacheFileExists = False
        if romPath is not None:
            gameFileName = os.path.split(romPath)[1]
            cacheFileName = os.path.join(self.cachedir, systemId, gameFileName) + '.xml'
            cacheFileExists = os.path.exists(cacheFileName) 

            # If this is a zipfile, get the gamename and crc from inside the zip
            if os.path.splitext(romPath)[1].lower() == '.zip':
                zf = zipfile.ZipFile(romPath, 'r')
                info = zf.infolist()
                # This only works if there is one file in the zip
                if len(info) == 1:
                    romName = info[0].filename

        if romName is not None:
            self.parameters['romnom'] = romName
        else:
            self.parameters['romnom'] = gameFileName

        self.parameters['crc'] = None
        if crc is not None:
            self.parameters['crc'] = crc
        elif romPath is not None and cacheFileExists is False:
            crc = get_crc(romPath)
            if crc is None:
                # If none is returned it means an empty CRC file was found, if
                # we are not forcing updates, go ahead and report rom not found
                if updateCache is False:
                    raise RomNotFoundError(self.parameters['systemeid'], self.parameters['romnom'], None)
            else:
                self.parameters['crc'] = crc
        
        # Only issue a command if there is no cache file or we want to update the cache file
        if updateCache is True or cacheFileExists is False:
            try:
                xml = self.SendRequest()
            except InvalidResponseError:
                # Retry without the CRC and stripped name
                del self.parameters['crc']
                self.parameters['romnom'] = self.parameters['romnom'].replace('[','(').split('(')[0].strip()
                try:
                    xml = self.SendRequest()
                except InvalidResponseError as e:
                    # Retry with Game Title
                    self.parameters['romnom'] = gameTitle
                    try:
                        xml = self.SendRequest()
                    except InvalidResponseError as e:
                        with open(romPath+'.crc', 'w') as f:
                            # Create an empty file a user can fill in with a CRC
                            f.close()
                        raise RomNotFoundError(self.parameters['systemeid'], self.parameters['romnom'], e.response)

            if not os.path.exists(os.path.dirname(cacheFileName)):
                try:
                    os.makedirs(os.path.dirname(cacheFileName))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            with open(cacheFileName, 'w') as f:
                f.write(xml.encode('utf-8'))
                f.close()

            self.root = ET.fromstring(xml.encode('utf-8'))

            if self.verbose:
                print("Created GameInfo class for %s." % self.parameters['romnom'])
        else:
            self.root = ET.parse(cacheFileName)
            if self.verbose:
                print("    Using cached xml file: %s." % cacheFileName)

    def GetAvailableMedia(self):
        """
        Media Dictionary looks like this:
          --mediaCategory--   --list of mediaEntries--
        { 'logosmonochrome': [{'url': 'http...', 'region': 'jp', 'crc': 'XYZ', 'md5': 'XXX', 'sha1': 'YYY'}, ...]},
        ...
        """
        if self.verbose:
            print("Getting media for %s." % self.parameters['romnom'])

        try:
            jue = self.root.find('jeu')
            medias = jue.find('medias')
            if medias is None:
                raise MediaNotFoundError
        except:
            return None

        return get_media(medias, self.verbose)

###############################################################################
# EXCEPTIONS
###############################################################################

class Error(Exception):
    pass

class InvalidResponseError(Error):
    def __init__(self, url, response):
        self.url = url
        self.response = response
    def __str__(self):
        # Python 2.7 only supports ASCII in exceptions, so don't include response with may contain unicode
        return "InvalidResponseError\n  URL: %s" % (self.url)

class RomNotFoundError(Error):
    def __init__(self, systemId, romName, response):
        self.systemId = systemId
        self.romName = romName
        self.reponse = response
    def __str__(self):
        # Python 2.7 only supports ASCII in exceptions, so don't include response with may contain unicode
        return "RomNotFoundError\n  SystemId: %s, RomName: %s" % (self.systemId, self.romName)

class MediaNotFoundError(Error):
    pass

###############################################################################
# GLOBAL FUNCTIONS
###############################################################################

def get_media( medias, verbose=False ):
    availableMedia = {}
    parse_media_parent( medias, availableMedia, verbose )
    return availableMedia

def parse_media_parent( parent, availableMedia, verbose=False ):
    for child in parent:
        # Check if this child is a parent(has children) and recursively call
        if len(child.getchildren()) > 0:
            parse_media_parent( child, availableMedia, verbose)
        else:
            element = parse_media_element( child )
            add_element_to_media( availableMedia, element, verbose )

def add_element_to_media( availableMedia, element, verbose=False ):
    # Work around for bug in xml from screen scaper, bezel names are inconsistent
    if element['name'].find('bezel-') is not -1:
        element['name'] = 'bezel'+element['name'].strip('bezel-')
    if element['name'] not in availableMedia:
        availableMedia[element['name']] = {}
    if element['locale'] not in availableMedia[element['name']]:
        if verbose is True:
            print("  Found %s (%s)" % (element['name'],element['locale']))
        availableMedia[element['name']][element['locale']] = {}
    availableMedia[element['name']][element['locale']][element['type']] = element['text']

def parse_media_element( child ):
    """
    Returns dictionary:
    { 'name': 'xyz', 'type': 'crc', 'locale': 'us', 'text': 'blah...' }
    (type can be: crc, md5, sha1, or url)
    """
    
    mediaElement = {}
    # extract the postfixes from the media tag
    # Eg. media_logomonochrome_jp_crc or media_logomonochrome_jp
    postfixes = child.tag.split('media_')[1].split('_')
    name = postfixes[0]
    locale = 'all'
    if len(postfixes) is 1:
        # URL has an empty postfix, it must be a URL
        elementType = 'url'
    elif len(postfixes) is 2:
        # URL has one postfix, that can specify a type or be a locale + url
        if postfixes[1] in ['crc','md5','sha1']:
            elementType = postfixes[1]
        else:
            locale = postfixes[1] 
            elementType = 'url'
    else:
        locale = postfixes[1]
        elementType = postfixes[2]
    
    mediaElement['name'] = name
    mediaElement['type'] = elementType
    mediaElement['locale'] = locale
    mediaElement['text'] = child.text

    return mediaElement

def crc32_from_file(filename):
    print("    Calculating CRC on %s..." % filename)
    prev = 0
    for eachLine in open(filename,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)

###############################################################################
# BASIC TESTS
###############################################################################

def main():
    import settings
    test = 3

    # import pdb; pdb.set_trace()
    if test == 1:
        ui = UserInfo(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, True)
        info = ui.GetUserInfo()

    if test == 2:
        sl = SystemList(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, False, True)
        slist = sl.GetSystemList()
        info = sl.GetInfo('1')
        media = sl.GetAvailableMedia('1')

    if test == 3:
        try:
            # gi = GameInfo(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, '26', 'D:/emulation/roms/a2600/Warlords (1981) (Atari).zip', verbose=True)
            gi = GameInfo(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, '4', 'D:/emulation/roms/snes/Super Mario World (U).ZIP', verbose=True)
            # gi = GameInfo(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, '23', 'D:/emulation/roms/dreamcast/Ikaruga (Japan).zip', verbose=True)
            media = gi.GetAvailableMedia()
        except:
            pass

if __name__ == "__main__":
    main()
