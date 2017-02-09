# coding=<utf-8>
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
    def __init__(self, devid, devpassword, softname, ssid, sspassword, updateSystems=False, verbose=False):
        super(SystemList, self).__init__(devid, devpassword, softname, ssid, sspassword, verbose)
        if updateSystems or not os.path.isfile( SS_SYSTEM_XML_FILE ):
            self.command = SS_SYSTEMS_LIST_CMD
            f = open(SS_SYSTEM_XML_FILE, 'w')
            f.write(self.SendRequest.encode('utf-8'))
            f.close()
        self.root = ET.parse(SS_SYSTEM_XML_FILE)
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

        availableMedia = {'logosmonochrome':[],'wheels':[],'wheelscarbon':[],'wheelscarbonvierge':[],'photos':[],'video':[],'fanart':[],'backgrounds':[],'screenmarquees':[],'screenmarqueesvierges':[],'boxs3dvierge':[],'support2dvierge':[],'controleur':[],'illustration':[],'bezels':[]}

        try:
            medias = system.find('medias')
        except:
            return availableMedia

        topLevelMedia = ['video','fanart',]
        twoLevelMedia = ['bezels',]

        return get_media(medias, availableMedia, topLevelMedia, twoLevelMedia, self.verbose)

class GameInfo(ScreenScraper):
    """ This class is used to obtain the game information and associated media. """
    def __init__(self, devid, devpassword, softname, ssid, sspassword, systemId, romPath=None, romName=None, crc=None, md5=None, sha1=None, romType=None, romSize=None, verbose=False):
        super(GameInfo, self).__init__(devid, devpassword, softname, ssid, sspassword, verbose)

        self.command = SS_GAME_INFO_CMD
        if crc is not None:
            self.parameters['crc'] = crc
        if md5 is not None:
            self.parameters['md5'] = md5
        if sha1 is not None:
            self.parameters['sha1'] = sha1
        if systemId is not None:
            self.parameters['systemeid'] = systemId
        if romType is not None:
            self.parameters['romtype'] = romType
        if romName is not None:
            self.parameters['romnom'] = romName
        if romSize is not None:
            self.parameters['romtaille'] = romSize

        if romPath is not None:
            gameFileName = os.path.split(romPath)[1]
            # If this is a zipfile, get the gamename and crc from inside the zip
            if os.path.splitext(romPath)[1].lower() == '.zip':
                zf = zipfile.ZipFile(romPath, 'r')
                info = zf.infolist()
                # This only works if there is one file in the zip
                if len(info) == 1:
                    self.parameters['romnom'] = info[0].filename
                    self.parameters['crc'] = "%08X" % info[0].CRC
                else:
                    self.parameters['romnom'] = gameFileName
                    self.parameters['crc'] = crc32_from_file(romPath)
            else:
                self.parameters['romnom'] = gameFileName
                self.parameters['crc'] = crc32_from_file(romPath)

        try:
            xml = self.SendRequest()
        except InvalidResponseError:
            del self.parameters['crc']
            try:
                # Retry one more time without the CRC
                xml = self.SendRequest()
            except InvalidResponseError as e:
                raise RomNotFoundError(self.parameters['systemeid'], self.parameters['romnom'], e.response)

        self.root = ET.fromstring(xml.encode('utf-8'))
        if self.verbose:
            print("Created GameInfo class for %s." % self.parameters['romnom'])

    def GetAvailableMedia(self):
        """
        Media Dictionary looks like this:
          --mediaCategory--   --list of mediaEntries--
        { 'logosmonochrome': [{'url': 'http...', 'region': 'jp', 'crc': 'XYZ', 'md5': 'XXX', 'sha1': 'YYY'}, ...]},
        ...
        """
        if self.verbose:
            print("Getting media for %s." % self.parameters['romnom'])

        mediaCategories = ['screenshot','fanart','video','marquee','screenmarquee','wheels','wheelscarbon','wheelssteel','boitiers','boxs','supports','manuels',]
        # availableMedia = {'screenshot':[],'':[],'fanart':[],'video':[],'marquee':[],'screenmarquee':[],'wheels':[],'wheelscarbon':[],'wheelssteel':[],'boitiers':[],'boxs':[],'supports':[],'manuels':[]}

        try:
            jue = self.root.find('jeu')
            medias = jue.find('medias')
            if medias is None:
                raise MediaNotFoundError
        except:
            return None

        topLevelMedia = ['screenshot','video','fanart','marquee','screenmarquee',]
        twoLevelMedia = ['boitiers','boxs','supports',]

        return get_media(medias, mediaCategories, topLevelMedia, twoLevelMedia, self.verbose)

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

def get_media( medias, mediaCategories, topLevelMedia=[], twoLevelMedia=[], verbose=False ):
    availableMedia = {}
    # Step through each type of media
    for mediaCategory in mediaCategories:
        # Add media_ to match screenscraper format
        foundMedia = medias.find('media_'+mediaCategory)
        if foundMedia is None:
            # No media of this type found for this system
            continue

        mediaEntry = {}
        # these doesn't have another level below it
        if mediaCategory in twoLevelMedia:
            for child in foundMedia:
                mediaEntry = create_media_entry(child)
                mediaCategory = child.tag.strip('media_')
                if mediaCategory not in availableMedia:
                    availableMedia[mediaCategory] = []
                availableMedia[mediaCategory].append(mediaEntry)
                if verbose:
                    print("  Found %s." % mediaCategory)
            # We already added to availableMedia, so go to next
            continue
        elif mediaCategory in topLevelMedia:
            mediaEntry['url'] = foundMedia.text
            for postfix in ['crc','md5','sha1']:
                foundMedia = medias.find('media_'+mediaCategory+'_'+postfix)
                if foundMedia is not None:
                    mediaEntry[postfix] = foundMedia.text
        else:
            mediaEntry = create_media_entry(foundMedia)
        if mediaCategory not in availableMedia:
            availableMedia[mediaCategory] = []
        availableMedia[mediaCategory].append(mediaEntry)
        if verbose:
            print("  Found %s." % mediaCategory)

    return availableMedia

def create_media_entry(foundMedia):
    mediaEntry = {}
    for child in foundMedia:
        # extract the postfixes from the media tag
        # Eg. media_logomonochrome_jp_crc or media_logomonochrome_jp
        postfixes = child.tag.split('media_')[1].split('_')
        locale = postfixes[1]
        try:
            entryType = postfixes[2]
        except:
            # URL has an empty postfix
            entryType = 'url'
        mediaEntry[entryType] = child.text
    return mediaEntry

def crc32_from_file(filename):
    buf = open(filename,'rb').read()
    buf = (binascii.crc32(buf) & 0xFFFFFFFF)
    return "%08X" % buf

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
        sl = SystemList(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, True)
        slist = sl.GetSystemList()
        info = sl.GetInfo('1')
        media = sl.GetAvailableMedia('1')

    if test == 3:
        try:
            gi = GameInfo(settings.devid, settings.devpassword, settings.softname, settings.ssid, settings.sspassword, '26', 'D:/emulation/roms/a2600/Warlords (1981) (Atari).zip', verbose=True)
            media = gi.GetAvailableMedia()
        except:
            pass

if __name__ == "__main__":
    main()
