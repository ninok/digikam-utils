# Collection of utility scripts for Digikam

The below scripts access the SQlite database of Digikam.
They should also work with other database engines with small adoptions.

## move_duplicates.py

Finds exact duplicates in Digikams database, i.e. images with the same unique hash.
Allows moving the duplicates out of the album into a different folder and removes
entries of moved files from the Digikam database. 

## safe_remove_duplicates.py

Verifies that all images in a given folder are already in the Digikam database and
also verifies that the md5 sum of the fiels matches, to prevent that files in the
database got corrupted after beeing imported.
This script is meant to be executed after duplicates.py to makes sure to not delete
files where no copy is in the database anymore.