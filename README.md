# faa-dof-gp #
This library provides the ability to read the [Federal Aviation Administration (FAA) Terrain and Obstacles Data (TOD) Team - Digital Obstacle File (DOF) files](https://nfdc.faa.gov/tod/public/TOD_DOF.html).

## faadof.py ##
Provides utilities for importing FAA DOF data into a geodatabase.

## remotezip.py ##
Code [posted on StackOverflow by João Pinto](http://stackoverflow.com/a/7843535).
Reads remote ZIP files using HTTP range requests.


## TO DO ##
* Add ability to read the latest zip file from [FAA DOF site](https://nfdc.faa.gov/tod/public/DOFS/) and extract only the desired text file.  (E.g., extract only the data for WA without having to download the whole zip file.)


