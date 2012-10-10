faa-dof-gp
==========

Written by [Jeff Jacobson] for [Washington State Department of Transportation (WSDOT) GIS & Roadway Data Office].


## Summary ##

This library provides the ability to read the [Federal Aviation Administration (FAA) Terrain and Obstacles Data (TOD) Team - Digital Obstacle File (DOF) files].

## Dependencies ##

* ArcGIS Desktop must be installed on computer.  (Having just ArcGIS Server instead of ArcGIS Desktop may also work, but has not been tested.)
* ArcView license level should be sufficient.

## Modules ##

### faadof.py ###
Provides utilities for importing FAA DOF data into a geodatabase.

### remotezip.py ###
Reads remote ZIP files using HTTP range requests.  This allows a file contained in a remote ZIP archive to be downloaded and extracted without the need to download the *entire* ZIP archive.
Code [posted on StackOverflow] by [João Pinto].

## Licensing ##
Licensed under the [CC BY-SA 3.0 License].

## Use ##

### Getting the Python scripts onto your computer ###
If you are reading these instructions on GitHub then the first thing you will need to do is copy the files to your computer.  You can download and extract [a zip archive] (or if you know how to use `git` you can use `git clone`).

### Running the script ###
Run `Scripts/faadof.py`.  This will download the obstacle data for Washington state from the FAA website and copy it into a file geodatabase.  You can provide an optional parameter to specify the path to the output file geodatabase.  If this parameter is omitted the output path will default to `../FaaObstruction.gdb`.

    faadof.py "c:\example\FAADOF.gdb"

If you run the script again, the script will check the FAA website to see if there is any data newer than what is in the existing file geodatabase.  If updates are detected then the file geodatabase will be updated with the latest data.

### Using as a Python module ###
You can import `faadof.py` as a module in your own Python script if you need to use data other than that of WA.

```python
import sys, os, faadof

# Get the parameter for the output GDB.
if len(sys.argv) > 1:
	gdbPath = os.path.abspath(sys.argv[1])
else:
	gdbPath = os.path.abspath("../FaaObstruction.gdb")

currencyDate = None
if arcpy.Exists(gdbPath):
	# Get the currency date
	currencyDate = faadof.getCurrencyDate(gdbPath)
	
print "Downloading DOFs..."
dofFilePaths = faadof.downloadDofs(datafiles=('56-WY.DAT'),lastCurrencyDate=currencyDate);

if dofFilePaths is not None:
	
	print "Creating new geodatabase: %s..." % gdbPath
	faadof.createDofGdb(gdbPath)
	
	print "Importing data..."
	faadof.readDofsIntoGdb(gdbPath, dofFilePaths)

print "Finished"
```

[Jeff Jacobson]: https://github.com/JeffJacobson
[Washington State Department of Transportation (WSDOT) GIS & Roadway Data Office]: http://www.wsdot.wa.gov/mapsdata/grdo_home.htm
[Federal Aviation Administration (FAA) Terrain and Obstacles Data (TOD) Team - Digital Obstacle File (DOF) files]: http://tod.faa.gov/tod/public/TOD_DOF.html
[posted on StackOverflow]: http://stackoverflow.com/a/7843535
[João Pinto]: http://stackoverflow.com/users/401041/joao-pinto
[a zip archive]: https://github.com/WSDOT-GIS/faa-dof-gp/zipball/master
[CC BY-SA 3.0 License]: http://creativecommons.org/licenses/by-sa/3.0/