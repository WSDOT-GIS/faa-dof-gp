"""
Read remote ZIP files using HTTP range requests
@author: João Pinto (http://stackoverflow.com/users/401041/joao-pinto)
@see: http://stackoverflow.com/a/7843535
@todo: The script does not work under Windows 7 with Python 2.6 (that comes with ArcGIS 10).  Fix it (or wait until ArcGIS 10.1)
"""
import struct
import urllib2
import zlib
import cStringIO
from zipfile import ZipInfo, ZipExtFile, ZipInfo
from os.path import join, basename

# The code is mostly adatpted from the zipfile module
# NOTE: ZIP64 is not supported

# The "end of central directory" structure, magic number, size, and indices
# (section V.I in the format document)
structEndArchive = "<4s4H2LH"
stringEndArchive = "PK\005\006"
sizeEndCentDir = struct.calcsize(structEndArchive)

_ECD_SIGNATURE = 0
_ECD_DISK_NUMBER = 1
_ECD_DISK_START = 2
_ECD_ENTRIES_THIS_DISK = 3
_ECD_ENTRIES_TOTAL = 4
_ECD_SIZE = 5
_ECD_OFFSET = 6
_ECD_COMMENT_SIZE = 7
# These last two indices are not part of the structure as defined in the
# spec, but they are used internally by this module as a convenience
_ECD_COMMENT = 8
_ECD_LOCATION = 9

# The "central directory" structure, magic number, size, and indices
# of entries in the structure (section V.F in the format document)
structCentralDir = "<4s4B4HL2L5H2L"
stringCentralDir = "PK\001\002"
sizeCentralDir = struct.calcsize(structCentralDir)

# indexes of entries in the central directory structure
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18

# The "local file header" structure, magic number, size, and indices
# (section V.A in the format document)
structFileHeader = "<4s2B4HL2L2H"
stringFileHeader = "PK\003\004"
sizeFileHeader = struct.calcsize(structFileHeader)

_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11


def _http_get_partial_data(url, start_range, end_range=None):
    req = urllib2.Request(url)
    range_header = "bytes=%s" % start_range
    if end_range is not None:
        range_header += "-%s" % end_range
    req.headers['Range'] = range_header
    f = urllib2.urlopen(req)    
    return f


def _EndRecData(url):
    """Return data from the "End of Central Directory" record, or None.

    The data is a list of the nine items in the ZIP "End of central dir"
    record followed by a tenth item, the file seek offset of this record."""
    ECD = _http_get_partial_data(url, -sizeEndCentDir)
    content_range =  ECD.headers.get('Content-Range')
    filesize = int(content_range.split('/')[1]) if content_range and '/' in content_range else 0
    data = ECD.read()
    ECD.close() 
    if data[0:4] == stringEndArchive and data[-2:] == "\000\000":
        # the signature is correct and there's no comment, unpack structure
        endrec = struct.unpack(structEndArchive, data)
        endrec = list(endrec)

        # Append a blank comment and record start offset
        endrec.append("")
        endrec.append(filesize - sizeEndCentDir)
        return endrec
    # Either this is not a ZIP file, or it is a ZIP file with an archive
    # comment.  Search the end of the file for the "end of central directory"
    # record signature. The comment is the last item in the ZIP file and may be
    # up to 64K long.  It is assumed that the "end of central directory" magic
    # number does not appear in the comment.

    # Search by retrieving chunks of 256, 1k and 64k
    try_ranges = (1 << 8, 1 << 10, 1 << 16)
    for check_range in try_ranges:
        ECD = _http_get_partial_data(url, -(check_range + sizeEndCentDir))      
        data = ECD.read()       
        content_range =  ECD.headers.get('Content-Range')       
        ECD.close()
        download_start = content_range.split('-')[0]
        start = data.rfind(stringEndArchive)        
        if start >= 0:          
            # found the magic number; attempt to unpack and interpret
            recData = data[start:start+sizeEndCentDir]
            endrec = list(struct.unpack(structEndArchive, recData))
            commentSize = endrec[_ECD_COMMENT_SIZE] #as claimed by the zip file
            comment = data[start+sizeEndCentDir:start+sizeEndCentDir+commentSize]
            endrec.append(comment)
            endrec.append(download_start + start)           
            return endrec

    raise IOError


class HTTPZipFile:
    def __init__(self, url):
        self.url = url
        self.NameToInfo = {}    # Find file info given name
        self.filelist = []      # List of ZipInfo instances for archive
        self.pwd = None
        self.comment = ''
        self.debug = 0
        self._RealGetContents()     

    def _RealGetContents(self):
        """Read in the table of contents for the ZIP file."""
        try:
            endrec = _EndRecData(self.url)
        except IOError:
            raise BadZipfile("File is not a zip file")
        if not endrec:
            raise BadZipfile, "File is not a zip file"
        if self.debug > 1:
            print endrec
        size_cd = endrec[_ECD_SIZE]             # bytes in central directory
        offset_cd = endrec[_ECD_OFFSET]         # offset of central directory
        self.comment = endrec[_ECD_COMMENT]     # archive comment

        # "concat" is zero, unless zip was concatenated to another file
        concat = endrec[_ECD_LOCATION] - size_cd - offset_cd
        #if endrec[_ECD_SIGNATURE] == stringEndArchive64:
        #   # If Zip64 extension structures are present, account for them
        #   concat -= (sizeEndCentDir64 + sizeEndCentDir64Locator)

        if self.debug > 2:
            inferred = concat + offset_cd
            print "given, inferred, offset", offset_cd, inferred, concat
        # self.start_dir:  Position of start of central directory
        self.start_dir = offset_cd + concat
        ECD = _http_get_partial_data(self.url, self.start_dir, self.start_dir+size_cd-1)
        data = ECD.read()
        ECD.close()
        fp = cStringIO.StringIO(data)               
        total = 0
        while total < size_cd:
            centdir = fp.read(sizeCentralDir)
            if centdir[0:4] != stringCentralDir:
                raise BadZipfile, "Bad magic number for central directory"
            centdir = struct.unpack(structCentralDir, centdir)
            if self.debug > 2:
                print centdir
            filename = fp.read(centdir[_CD_FILENAME_LENGTH])
            # Create ZipInfo instance to store file information
            x = ZipInfo(filename)
            x.extra = fp.read(centdir[_CD_EXTRA_FIELD_LENGTH])
            x.comment = fp.read(centdir[_CD_COMMENT_LENGTH])
            x.header_offset = centdir[_CD_LOCAL_HEADER_OFFSET]
            (x.create_version, x.create_system, x.extract_version, x.reserved,
                x.flag_bits, x.compress_type, t, d,
                x.CRC, x.compress_size, x.file_size) = centdir[1:12]
            x.volume, x.internal_attr, x.external_attr = centdir[15:18]
            # Convert date/time code to (year, month, day, hour, min, sec)
            x._raw_time = t
            x.date_time = ( (d>>9)+1980, (d>>5)&0xF, d&0x1F,
                                     t>>11, (t>>5)&0x3F, (t&0x1F) * 2 )

            x._decodeExtra()
            x.header_offset = x.header_offset + concat
            x.filename = x._decodeFilename()
            self.filelist.append(x)
            self.NameToInfo[x.filename] = x

            # update total bytes read from central directory
            total = (total + sizeCentralDir + centdir[_CD_FILENAME_LENGTH]
                     + centdir[_CD_EXTRA_FIELD_LENGTH]
                     + centdir[_CD_COMMENT_LENGTH])

        if self.debug > 2:
            print "total", total

    def namelist(self):
        """Return a list of file names in the archive."""
        l = []
        for data in self.filelist:
            l.append(data.filename)
        return l

    def infolist(self):
        """Return a list of class ZipInfo instances for files in the
        archive."""
        return self.filelist

    def printdir(self):
        """Print a table of contents for the zip file."""
        print "%-46s %19s %12s" % ("File Name", "Modified    ", "Size")
        for zinfo in self.filelist:
            date = "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time[:6]
            print "%-46s %s %12d" % (zinfo.filename, date, zinfo.file_size)

    def getinfo(self, name):
        """Return the instance of ZipInfo given 'name'."""
        info = self.NameToInfo.get(name)
        if info is None:
            raise KeyError(
                'There is no item named %r in the archive' % name)

        return info         

    def open(self, name, pwd=None):
        """Return file-like object for 'name'."""
        if not self.url:
            raise RuntimeError, \
                  "Attempt to read ZIP archive that was already closed"
        zinfo = self.getinfo(name)
        offset = zinfo.header_offset
        f = _http_get_partial_data(self.url, offset, offset+sizeFileHeader-1)
        fheader = f.read()
        f.close()

        fheader = struct.unpack(structFileHeader, fheader)
        offset += sizeFileHeader
        f = _http_get_partial_data(self.url, offset, offset+fheader[_FH_FILENAME_LENGTH]-1)
        fname = f.read()
        f.close()

        if fname != zinfo.orig_filename:
            raise BadZipfile, \
                      'File name in directory "%s" and header "%s" differ.' % (
                          zinfo.orig_filename, fname)

        is_encrypted = zinfo.flag_bits & 0x1
        if is_encrypted:
            raise RuntimeError, "File %s is encrypted, " \
                  "not supported." % name

        offset += fheader[_FH_FILENAME_LENGTH]+fheader[_FH_EXTRA_FIELD_LENGTH]
        f = _http_get_partial_data(self.url, offset, offset+fheader[_FH_COMPRESSED_SIZE]-1)
        data = f.read()
        return ZipExtFile(cStringIO.StringIO(data), 'r', zinfo)


if __name__ == "__main__":
    # Some tests
    link="http://dfn.dl.sourceforge.net/project/filezilla/FileZilla_Client/3.5.1/FileZilla_3.5.1_win32.zip"
    hzfile = HTTPZipFile(link)
    hzfile.printdir()
    for fname in ('GPL.html', 'resources/blukis/48x48/filter.png', 'resources/finished.wav'):
        source_name = join('FileZilla-3.5.1', fname)
        dest_fname = join('/tmp', basename(fname))
        print "Extracing %s to %s" % (source_name, dest_fname)
        with hzfile.open(source_name) as f:
            data = f.read()
            new_file = open(dest_fname, 'w')
            new_file.write(data)
            new_file.close()