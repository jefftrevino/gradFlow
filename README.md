# Lick-Wilmerding High School Course Enrollment Flow Chart

### Dependencies
--*rsvg-convert* convert from .svg to .pdf

--*pandoc* convert from .svg to .html

--*Google Drive symlink* `~/mydrive` should be symbolically linked to a location in Google Drive.

### Automatically convert and synch
To convert a revised .svg file to .pdf and .html, and then synch all three files to Google Drive,
1. Open up the Terminal in the repository directory.
2. `source convert_and_synch_to_drive.sh`
