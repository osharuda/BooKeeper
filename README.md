# BooKeeper

This small script is intended to scan your directory with documents and get meaningfull information required to organize your documents. 
* Supported document files are DJVU and PDF.
* Recursive archive (zip, rar, 7z, tar.gz) scanning is supported.

Data is saved into sqlite3 database.

## Dependencies
This script is not inteded to be run on anything but Linux. If you want you may adapt it for other operational systems.

The following packages are required:
```
# Install required packages
sudo apt update
sudo apt install python3 python3-venv sqlite3 poppler-utils djvulibre-bin imagemagick unzip unrar 7zip tesseract-ocr
```

It is recommended to install language support packages for tesseract-ocr. For example:
```
sudo apt install tesseract-ocr-eng tesseract-ocr-osd tesseract-ocr-rus
```

## Installing and mounting RAM drive
Unpacking archives requires some temporary storage. It's better to have a ram drive. Let's say you want 8G ramdrive by
`/mnt/ramdrive` location:

In order to make one run this:
```
sudo mkdir /mnt/ramdrive
sudo mount -t tmpfs -o size=8g tmpfs /mnt/ramdrive
```

To unmount it:
```
sudo umount /mnt/ramdrive
sudo rm -r /mnt/ramdrive
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

| Name                  | Value |
|:----------------------|:------------------|
| `"ram_drive_path"`    | Path to the directory with mounted RAM drive |
| `"libraries"`         | List of the path's with your documents. |
| `"work_path"`         | Path where do you want to keep results (database and log file) |
| `"db_file_name"`      | Name of the database file (just a basename without path) |
| `"log_file_name"`     | Name of the log file (just a basename without path) |
| `"log_level"`         | Log level. Available values are: `Diagnostic`, `Log`, `Warning`, `Error`.|
| `"language_option"`   | Language option for tesseract. See `man tesseract`, `-l` option. |

## Running
To run script you have to create virtual environment first by running:
```
./make_venv.sh
```

After that run 
```
./scan.sh <config file>
```

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
    foreign key(parent_arch_hash) references archives(hash),
    foreign key(hash) references archives(hash)
);

CREATE TABLE bad_files( 
    id int  primary key,
    file_name string,
    file_type int,
    hash string,
    archive_hash string,
    foreign key(archive_hash) references archives(hash)
);
```