#!/bin/bash

RAM_DISK_IMAGE_PATH='/mnt/ram_disk_image'
RAM_DRIVE_PATH='/mnt/ramdrive'
RAM_DISK_IMAGE="${RAM_DISK_IMAGE_PATH}/ram_disk.img"
RAM_DISK_LABEL='RAM'
RAM_SIZE_GB=8

set -e

echo 'Creating directories ...'
sudo mkdir -p ${RAM_DISK_IMAGE_PATH}
sudo chmod +w ${RAM_DISK_IMAGE_PATH}

sudo mkdir -p ${RAM_DRIVE_PATH}
sudo chmod +w ${RAM_DRIVE_PATH}

echo 'Mounting tmpfs ...'
sudo mount -t tmpfs -o size=${RAM_SIZE_GB}g tmpfs ${RAM_DISK_IMAGE_PATH}
echo 'Creating ram drive NTFS image ...'
touch ${RAM_DISK_IMAGE}
truncate -s ${RAM_SIZE_GB}G ${RAM_DISK_IMAGE}
echo 'type=83' | sudo sfdisk ${RAM_DISK_IMAGE}

LO_BLOCK_DEV=$(losetup -f)
sudo losetup -P ${LO_BLOCK_DEV} ${RAM_DISK_IMAGE}
sudo mkfs.ntfs ${LO_BLOCK_DEV} -L ${RAM_DISK_LABEL}

echo 'Mounting image ...'
sudo mount ${LO_BLOCK_DEV} ${RAM_DRIVE_PATH}
