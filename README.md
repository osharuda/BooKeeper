# BooKeeper

This small script is intended to scan your directory with documents and get meaningfull information required to organize your documents. 
* Supported document file types are PDF, DJVU, FB2, RTF, DOCX, ODT.
* Recursive archive (zip, rar, 7z, tar.gz) scanning is supported.

Data is saved into sqlite3 database.

## Dependencies
This script is not inteded to be run on anything but Linux. If you want you may adapt it for other operational systems.

The following packages are required:
```
# Install required packages
sudo apt update
sudo apt install python3 python3-venv sqlite3 poppler-utils djvulibre-bin imagemagick unzip unrar 7zip tesseract-ocr pandoc pandoc-data catdoc
```

It is recommended to install language support packages for tesseract-ocr. For example:
```
sudo apt install tesseract-ocr-eng tesseract-ocr-osd tesseract-ocr-rus
```

## Installing and mounting RAM drive
Unpacking archives requires some temporary storage. It's better to have a RAM drive for some reasons:
* You hard drive will last longer. Excessive IO is not good for neither SSD not HDD drives.
* There could be a problem with archives packed on Windows with non ASCII names. It might happen that such files names might violate POSIX limitation (NAME_MAX) which is typically 255 **bytes**, not characters. Windows uses UTF-16 to encode characters with two bytes per character, while UTF-8 use 1 byte for ASCII characters, but may use more bytes for a non-ASCII characters. In other words, the length of the file name is not easily predictable. Thus, some name may exceed this limit causing issues with extracting files from archive. The solution for this is to use NTFS for temporary RAM drive storage. 


Ok, there is a simple script (`ramdrv.sh`) which creates required RAM drive. It is configured to create 8GB NTFS RAM disk by `/mnt/ramdrive` location. Change script if you want other settings.

Just run this script. Warning it will require `sudo` permitions.
```
sudo ./ramdrv.sh
```

## Configuration file
You have to prepare configuration file as JSON file to run script. Below is a configuration file for the script:

```
{
  "ram_drive_path":  "/mnt/ramdrive",
  "libraries":       ["./test"],
  "work_path":       "./",
  "db_file_name":    "bookeeper_test.db",
  "log_file_name":   "bookeeper_test.log",
  "log_level":       "diagnostic",
  "language_option": "eng+rus"
}
```

The table below describes available options:

| Name                  | Value                                                                                |
|:----------------------|:-------------------------------------------------------------------------------------|
| `"ram_drive_path"`    | Path to the directory with mounted RAM drive                                         |
| `"libraries"`         | List of the path's with your documents.                                              |
| `"work_path"`         | Path where do you want to keep results (database and log file)                       |
| `"export_path"`       | Path where do you want to export books from you library, when you search for a book. |
| `"db_file_name"`      | Name of the database file (just a basename without path)                             |
| `"log_file_name"`     | Name of the log file (just a basename without path)                                  |
| `"log_level"`         | Log level. Available values are: `Diagnostic`, `Log`, `Warning`, `Error`.            |
| `"language_option"`   | Language option for tesseract. See `man tesseract`, `-l` option.                     |



There are also some debug (optional) values:
| Name                          | Value                                                                      |  
|:------------------------------|:---------------------------------------------------------------------------|
| `"delete_artifacts"`          | If 1, deletes temporary artifacts from the RAM drive. By default 1.        |
| `"delete_db_on_start"`        | If 1, deletes database on scan start. By default 0.                        |
| `"clear_ram_drive_on_start"`  | If 1, clears content of the RAM drive before program starts. By default 0. |

## Running
To run script you have to create virtual environment first by running:
```
./make_venv.sh
```

After that run 
```
./scan.sh <config file>
```
This script will take for a while, it depends on the size of your library. If you want to pause script execution press `Ctrl`-`C` and exit, if required.

Once database is built, run
```
./browse.sh <config file>
```

In order to searh for required documents. Select and right click on a book from search result for a context menu. You may either to inspect document information, or try to open it. If file is required to be unpacked from archive, it will be extracted to the RAM drive.

## Database structure

The following tables will have the output information.

```
CREATE TABLE books( 
    hash string primary key,
    size sqlite_int64,
    ocr bool,
    booktype int,
    page_count int,
    text_data string,
    tokens string
);

CREATE TABLE book_files( 
    id integer primary key,
    file_name string,
    archive_hash string,
    hash string,
    status int,
    foreign key(archive_hash) references archives(hash),
    foreign key(hash) references books(hash)
);

CREATE TABLE archives( 
    hash string primary key,
    file_type int,
    size sqlite_int64
);

CREATE TABLE archive_files( 
    id integer primary key,
    file_name string,
    hash string,
    parent_arch_hash string,
    status int,
    foreign key(parent_arch_hash) references archives(hash),
    foreign key(hash) references archives(hash)
);

CREATE TABLE bad_files( 
    id int  primary key,
    file_name string,
    file_type int,
    hash string,
    archive_hash string,
    error_code int,
    status int,
    foreign key(archive_hash) references archives(hash)
);

CREATE TABLE other_paths( 
    id integer primary key,
    path string,
    status int
);

CREATE TABLE other_files( 
    id integer primary key,
    path_id int,
    basename string,
    size sqlite_int64,
    hash string,
    status int,
    foreign key(path_id) references other_paths(id)
);

```