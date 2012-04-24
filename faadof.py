# -*- coding: utf-8 -*-
'''
Created on Apr 23, 2012

@author: JacobsJ
@todo: add command line parameters for gdb location and dof location
@todo: add optional command line parameter for which z value to use in geometry: above ground or above sea level column
'''

import os.path, re, datetime
import arcpy

_jdatere = re.compile("(?P<year>\d{4})(?P<days>\d{3})")
_wgs84 = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433],AUTHORITY["EPSG",4326]]'
_ngvd1929 = 'VERTCS["NGVD_1929",VDATUM["National_Geodetic_Vertical_Datum_1929"],PARAMETER["Vertical_Shift",0.0],PARAMETER["Direction",1.0],UNIT["Foot_US",0.3048006096012192],AUTHORITY["EPSG",5702]]'
_navd1988 = 'VERTCS["NAVD_1988",VDATUM["North_American_Vertical_Datum_1988"],PARAMETER["Vertical_Shift",0.0],PARAMETER["Direction",1.0],UNIT["Meter",1.0],AUTHORITY["EPSG",5703]]'

_zDate = datetime.date(2001, 3, 12) # Records on or after this date are in NAVD 1988.  Prior are NGVD 1929.

#def getCSDir():
#    subdir = "ArcGIS/Desktop10.0/Coordinate Systems"
#    # Try to get the programfiles(x86) directory.  (64-bit OS only)
#    if os.environ.has_key("programfiles(x86)"):
#        output = os.path.join(os.environ["programfiles(x86)"], subdir)
#        if os.path.exists(output):
#            return output
#    if os.environ.has_key("programfiles"):
#        output = os.path.join(os.environ["programfiles"], subdir)
#        return output
    

def julianDateToDate(jDate):
    match =_jdatere.match(jDate)
    if match:
        d = match.groupdict()
        year = int(d["year"])
        days = int(d["days"])
        date = datetime.date(year,1,1) + datetime.timedelta(days=days-1)
        return date

def dmsToDD(degrees, minutes, seconds, hemisphere):
    dd = degrees + (minutes / 60) + (seconds/3600)
    if hemisphere == "S" or hemisphere == "W":
        dd *= -1
    return dd

class Dms(object): 
    def __init__(self, degrees, minutes, seconds, hemisphere):
        self.degrees = degrees
        self.minutes = minutes
        self.seconds = seconds
        self.hemisphere = hemisphere
    def toDD(self):
        dd = self.degrees + (self.minutes / 60) + (self.seconds/3600)
        # Negate the value if hemisphere is south or west.
        if re.match("[SW]", self.hemisphere): 
            dd *= -1
        return dd
    def __str__(self, *args, **kwargs):
        return "%s %s %s %s" % (self.degrees, self.minutes, self.seconds, self.hemisphere)

    
class Obstacle(object):
    def __init__(self, line):
        self.orsCode = line[0:2]
        self.obstacleNumber = line[3:10]
        self.verificationStatus = line[10]
        self.countryId = line[12:15].rstrip()
        self.stateId = line[15:18].rstrip()
        self.cityName = line[18:34].rstrip()
        
        self.latitude = Dms(int(line[35:37]), int(line[38:40]), float(line[41:46]), line[46])
        self.longitude = Dms(int(line[48:51]), int(line[52:54]), float(line[55:60]), line[60])
        
        self.obstacleType = line[62:74].rstrip()
        self.quantity = int(line[75])
        self.aglHT = int(line[77:82])
        self.AmslHT = int(line[83:88])
        
        self.lighting = line[89]
        self.horizontalAccuracy = line[91].rstrip()
        self.verticalAccuracy = line[93].rstrip()
        self.markIndicator = line[95]
        
        self.faaStudyNo = line[97:111].rstrip()
        self.action = line[112]
        self.date = julianDateToDate(line[114:121])
    def __str__(self, *args, **kwargs):
        return object.__str__(self, *args, **kwargs)

def addObstacleToRow(row, obstacle):
    row.orsCode = obstacle.orsCode
    row.obstacleNo = obstacle.obstacleNumber
    row.verificationStatus = obstacle.verificationStatus
    row.countryId = obstacle.countryId
    row.stateId = obstacle.stateId
    row.cityName = obstacle.cityName
#    row.latitude = obstacle.latitude
#    row.longitude = obstacle.longitude
    row.obstacleType = obstacle.obstacleType
    row.quantity = obstacle.quantity
    row.aglHT = obstacle.aglHT
    row.AmslHT = obstacle.AmslHT
    row.lighting = obstacle.lighting
    row.horizontalAccuracy = obstacle.horizontalAccuracy
    row.verticalAccuracy = obstacle.verticalAccuracy
    row.markIndicator = obstacle.markIndicator
    row.faaStudyNo = obstacle.faaStudyNo
    row.action = obstacle.action
    row.date = str(obstacle.date) # Dates have to be set as strings
    
    point = arcpy.Point()
    point.X = obstacle.longitude.toDD()
    point.Y = obstacle.latitude.toDD()
    point.Z = obstacle.aglHT
    pointGeometry = arcpy.PointGeometry(point)
    row.shape = pointGeometry

def createDomains(gdbPath):
    """Creates file geodatabase domains for FAA Digital Obstacle Files.
    @param gdbPath: Path to a geodatabase.
    @author: Jeff Jacobson
    @organization: WSDOT
    """
    # Add Domains
    # ORS Codes
    domainName = "OrsCode"
    arcpy.CreateDomain_management(gdbPath, domainName, "ORS Code.  Indicates region (e.g., US State, country).", "TEXT")
    
    domainValues = [
                ["01", "Alabama"],
                ["02", "Alaska"],
                ["04", "Arizona"],
                ["05", "Arkansas"],
                ["06", "California"],
                ["08", "Colorado"],
                ["09", "Connecticut"],
                ["10", "Delaware"],
                ["11", "DC"],
                ["12", "Florida"],
                ["13", "Georgia"],
                ["15", "Hawaii"],
                ["16", "Idaho"],
                ["17", "Illinois"],
                ["18", "Indiana"],
                ["19", "Iowa"],
                ["20", "Kansas"],
                ["21", "Kentucky"],
                ["22", "Louisiana"],
                ["23", "Maine"],
                ["24", "Maryland"],
                ["25", "Massachusetts"],
                ["26", "Michigan"],
                ["27", "Minnesota"],
                ["28", "Mississippi"],
                ["29", "Missouri"],
                ["30", "Montana"],
                ["31", "Nebraska"],
                ["32", "Nevada"],
                ["33", "New Hampshire"],
                ["34", "New Jersey"],
                ["35", "New Mexico"],
                ["36", "New York"],
                ["37", "North Carolina"],
                ["38", "North Dakota"],
                ["39", "Ohio"],
                ["40", "Oklahoma"],
                ["41", "Oregon"],
                ["42", "Pennsylvania"],
                ["44", "Rhode Island"],
                ["45", "South Carolina"],
                ["46", "South Dakota"],
                ["47", "Tennessee"],
                ["48", "Texas"],
                ["49", "Utah"],
                ["50", "Vermont"],
                ["51", "Virginia"],
                ["53", "Washington"],
                ["54", "West Virginia"],
                ["55", "Wisconsin"],
                ["56", "Wyoming"],
                ["CA", "Canada"],
                ["MX", "Mexico"],
                ["PR", "Puerto Rico"],
                ["BS", "Bahamas"],["AG", "Antigua and Barbuda"],
                ["AI", "Anguilla"],
                ["AN", "Netherlands Antilles"],
                ["AW", "Aruba"],
                ["CU", "Cuba"],
                ["DO", "Dominican Republic"],
                ["GP", "Guadeloupe"],
                ["HN", "Honduras"],
                ["HT", "Haiti"],
                ["JM", "Jamaica"],
                ["KN", "St. Kitts and Nevis"],
                ["KY", "Cayman Islands"],
                ["MS", "Montserrat"],
                ["TC", "Turks and Caicos Islands"],
                ["VG", "British Virgin Islands"],
                ["VI", "Virgin Islands"],
                ["AS", "American Samoa"],
                ["FM", "Federated States of Micronesia"],
                ["GU", "Guam"],
                ["KI", "Kiribati"],
                ["MH", "Marshall Islands"],
                ["MI", "Midway Islands"],
                ["MP", "Northern Mariana Islands"],
                ["PW", "Palau"],
                ["RU", "Russia"],
                ["TK", "Tokelau"],
                ["WQ", "Wake Island"],
                ["WS", "Samoa"],
            ]
    
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code[0], code[1])
    
    # Verification Status
    domainName = "VerificationStatus"
    arcpy.CreateDomain_management(gdbPath, domainName, "Verification Status", "TEXT")
    arcpy.AddCodedValueToDomain_management(gdbPath, domainName, "O", "verified")
    arcpy.AddCodedValueToDomain_management(gdbPath, domainName, "U", "unverified")
    
    domainName = "LightingType"
    arcpy.CreateDomain_management(gdbPath, domainName, "Lighting Type", "TEXT")
    domainValues = {
        "R":  "Red",
        "D":  "Medium intensity White Strobe & Red", 
        "H":  "High Intensity White Strobe & Red", 
        "M": "Medium Intensity White Strobe", 
        "S" :  "High Intensity White Strobe", 
        "F" :  'Flood', 
        "C" : "Dual Medium Catenary", 
        "W": "Synchronized Red Lighting", 
        "L" : "Lighted (Type Unknown)", 
        "N":  "None", 
        "U":  "Unknown"
    }
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code, domainValues[code])
        
    domainName = "HorizontalAccuracy"
    arcpy.CreateDomain_management(gdbPath, domainName, "Horizontal Accuracy", "TEXT")
    domainValues = {
        "1": "+-20'",
        "2": "+-50'",
        "3": "+-100'",
        "4": "+-250'",
        "5": "+-500'",
        "6": "+-1000'",
        "7": "+-1/2 NM",
        "8": "+-1 NM",
        "9": "Unknown"
    }
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code, domainValues[code])
        
    domainName = "VerticalAccuracy"
    arcpy.CreateDomain_management(gdbPath, domainName, "Vertical Accuracy", "TEXT")
    domainValues = {
        "A": "+-3'",
        "B": "+-10'",
        "C": "+-20'",
        "D": "+-50'",
        "E": "+-125'",
        "F": "+-250'",
        "G": "+-500'",
        "H": "+-1000'",
        "I": "Unknown"
    }
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code, domainValues[code])
        
    domainName = "MarkIndicator"
    arcpy.CreateDomain_management(gdbPath, domainName, "Type of Marking", "TEXT")
    domainValues = {
        "P":   "Orange or Orange and White Paint",
        "W": "White Paint Only",
        "M":  "Marked",
        "F":   "Flag Marker",
        "S":   "Spherical Marker",
        "N":  "None",
        "U":  "Unknown"
    }
    
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code, domainValues[code])
    
    domainName = "Action"
    arcpy.CreateDomain_management(gdbPath, domainName, "Action", "TEXT")
    domainValues = {
        "A": "Add",
        "C": "Change",
        "D": "Dismantle"
    }
    
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code, domainValues[code])
    
    domainName = "StructureTypes"
    arcpy.CreateDomain_management(gdbPath, domainName, "Structure Types", "TEXT")
    domainValues = {
        "AG EQUIP":"agricultural equipment",
        "ARCH":"arch",
        "BALLOON":"balloon: tethered; weather; other reconnaissance",
        "BLDG":"building",
        "BLDG-TWR":"latticework greater than 20' on building",
        "BRIDGE":"bridge",
        "CATENARY":"catenary: transmission line span/wire/cable",
        "COOL TWR":"nuclear cooling tower",
        "CRANE":"crane: permanent",
        "CRANE T":"crane: temporary",
        "CTRL TWR":"airport control tower",
        "DAM":"Dam",
        "DOME":"Dome",
        "ELECTRICAL SYSTEM":"Electrical System",
        "ELEVATOR":"silo; grain elevator",
        "FENCE":"Fence",
        "GENERAL UTILITY":"General Utility",
        "LIGHTHOUSE":"Lighthouse",
        "MONUMENT":"Monument",
        "NAVAID":"airport navigational aid",
        "PLANT":"plant: multiple close structures used for industrial purposes",
        "POLE":"flag pole; light pole",
        "REFINERY":"refinery: multiple close structures used for purifying crude materials",
        "RIG":"oil rig",
        "SIGN":"Sign",
        "SPIRE":"spire: steeple",
        "STACK":"stack: smoke; industrial",
        "STADIUM":"Stadium",
        "T-L TWR":"transmission line tower; telephone pole",
        "TANK":"tank: water; fuel",
        "TOWER":"Tower",
        "TRAMWAY":"Tramway",
        "TREE":"Tree",
        "VEGETATION":"Vegetation",
        "WINDMILL":"windmill: wind turbine"
    }
    for code in domainValues:
        arcpy.AddCodedValueToDomain_management(gdbPath, domainName, code, domainValues[code])

def createDofFeatureClass(out_path, name, projection):
    arcpy.CreateFeatureclass_management(out_path, name, "POINT", None, None, "ENABLED", projection)
    fcPath = os.path.join(out_path, name)
    arcpy.AddField_management(fcPath, "OrsCode", "TEXT", None, None, 2, "ORS Code", "NON_NULLABLE", "REQUIRED", "OrsCode")
    arcpy.AddField_management(fcPath, "ObstacleNo", "TEXT", None, None, 7, "Obstacle Number", "NON_NULLABLE")
    arcpy.AddField_management(fcPath, "VerificationStatus", "TEXT", None, None, 1, "Verification Status", "NON_NULLABLE", "NON_REQUIRED", "VerificationStatus")
    arcpy.AddField_management(fcPath, "CountryId", "TEXT", None, None, 2, "Country Identifier")
    arcpy.AddField_management(fcPath, "StateId", "TEXT", None, None, 2, "State Identifier")
    arcpy.AddField_management(fcPath, "CityName", "TEXT", None, None, 16, "City Name")
    arcpy.AddField_management(fcPath, "ObstacleType", "TEXT", None, None, 12, "Obstacle Type", None, None, "StructureTypes")
    arcpy.AddField_management(fcPath, "Quantity", "SHORT")
    arcpy.AddField_management(fcPath, "AglHT", "SHORT", field_alias="Above Ground Level Height (Feet)")
    arcpy.AddField_management(fcPath, "AmslHt", "SHORT", field_alias="Above Mean Sea Level Height (Feet)")
    arcpy.AddField_management(fcPath, "Lighting", "TEXT", field_length=1, field_domain="LightingType")
    arcpy.AddField_management(fcPath, "HorizontalAccuracy", "TEXT", None, None, 1, "Horizontal Accuracy", None, None, "HorizontalAccuracy")
    arcpy.AddField_management(fcPath, "VerticalAccuracy", "TEXT", None, None, 1, "Vertical Accuracy", None, None, "VerticalAccuracy")
    arcpy.AddField_management(fcPath, "MarkIndicator", "TEXT", None, None, 1, "Mark Indicator", None, None, "Mark Indicator")
    arcpy.AddField_management(fcPath, "FaaStudyNo", "TEXT", None, None, 14, "FAA Study Number")
    arcpy.AddField_management(fcPath, "Action", "TEXT", None, None, 1, None, None, None, "Action")
    arcpy.AddField_management(fcPath, "Date", "DATE")


def createDofGdb(gdbPath):
    """Creates a file Geodatabase for FAA DOF data.  Creates the necessary domains as well.
    @param gdbParam: The path where the GDB will be created.
    """
    # Delete the GDB if it already exists.
    if arcpy.Exists(gdbPath):
        print "%s already exists.  Deleting..." % gdbPath
        arcpy.Delete_management(gdbPath)
    #Create a new GDB.
    print "Creating %s..." % gdbPath
    arcpy.CreateFileGDB_management(*os.path.split(gdbPath))
    print "Creating domains in %s..." % gdbPath
    createDomains(gdbPath)
    # Add feature classes
    print "Creating feature classes in %s..." % gdbPath
    createDofFeatureClass(gdbPath, "NAVD1988", _wgs84 + ',' + _navd1988)
    createDofFeatureClass(gdbPath, "NGVD1929", _wgs84 + ',' + _ngvd1929) 


#def readDofFile(dofPath):
#    """Reads DOF file and converts to Obstacle objects.
#    @param dofPath: Path to the DOF file
#    @param gdbPath: Path to the GDB.
#    """
#    obstacles = []
#    if os.path.exists(dofPath):
#        with open(dofPath) as f:
#            i = 0
#            for line in f:
#                if i == 0:
#                    pass # TODO: Do something with "Currency Date"
#                elif i >= 4:
#                    obstacle = Obstacle(line)
#                    print "%s,%s" % (str(obstacle.longitude), str(obstacle.latitude))
#                    print "%s %s" % (obstacle.longitude.toDD(), obstacle.latitude.toDD())
#                    obstacles.append(obstacle)
#                i += 1
#                
#    else:
#        raise "File not found: %s" % dofPath
#    return obstacles

def readDofIntoGdb(dofPath, gdbPath):
    """Reads DOF file into file geodatabase.
    @param dofPath: Path to the DOF file
    @param gdbPath: Path to the GDB.
    """
    if os.path.exists(dofPath):
        cursor88 = arcpy.InsertCursor(os.path.join(gdbPath, "NAVD1988"))
        cursor29 = arcpy.InsertCursor(os.path.join(gdbPath, "NGVD1929"))
        with open(dofPath) as f:
            i = 0
            for line in f:
                if i == 0:
                    print "Currency date is %s." % line
                    # TODO: Do something with "Currency Date"
                elif i >= 4:
                    obstacle = Obstacle(line)
                    row = None
                    if obstacle.date >= _zDate:
                        row = cursor88.newRow()
                        addObstacleToRow(row, obstacle)
                        cursor88.insertRow(row)
                    else:
                        row = cursor29.newRow()
                        addObstacleToRow(row, obstacle)
                        try:
                            cursor29.insertRow(row)
                        except RuntimeError, err:
                            print "%s: %s" % (err, obstacle.stateId)
                            raise
                    
                i += 1
        del cursor88, cursor29
    else:
        raise "File not found: %s" % dofPath

gdbPath = os.path.abspath("../FaaObstruction.gdb")
dofPath = os.path.abspath("../Sample/53-WA.Dat")

print "Creating new geodatabase: %s..." % gdbPath
createDofGdb(gdbPath)

print "Importing data from %s into %s..." % (dofPath, gdbPath)
readDofIntoGdb(dofPath, gdbPath)

print "Finished"

