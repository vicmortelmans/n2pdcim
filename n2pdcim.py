#!/usr/bin/env python
import datetime
import exifread
import glob
import logging
import nmcli
import os
import os.path
import requests
import shutil
import subprocess
import time
import traceback
import urllib.parse
from bs4 import BeautifulSoup

#this script is for downloading raw files from an USB drive with a card that is reserved
#for digitizing black and white negative images. This card should contain a file in root
#named "n2p", and NO root file named "ez Share *", because then the usbdcim.py script will
#run through usbdcim.py and unmount the drive prematurely.

#the user experience should be to connect the camera/drive, hear two beeps for confirmation, 
#all files being moved (!) and the processing starting in the background; after the last
#file is moved, three confirmation beeps are heard and the user will unplug the camera. 

#version
_VERSION = 1.1

#temporary workspace while downloaden/uploading files
_TEMP = os.path.expanduser("~/Pictures")
os.makedirs(_TEMP, exist_ok=True)

#path where the find automounted usb drives
_USB = os.path.expanduser("/media")

#path of the n2p script
_N2P_ = os.path.expanduser("~/bin/n2p_2025")

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d %(funcName)s] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG)

def main():

    logging.info(f"n2pdcim.py version {_VERSION} is started")

    try:

        #endless polling loop for (automatically mounted) USB drive
        while True: 

            #import pdb; pdb.set_trace()

            usb_name, usb_path = find_first_mounted_n2pdcim_usb_name()

            if usb_name:

                #start a session: two-beep confirm and session dir in ~/Pictures
                os.system('spd-say "Starting to read card"')
                session = new_session_name()
                counter = 1

                try:

                    filenames = get_list_of_filenames_on_camera(usb_path)
                    
                    for (path, filename) in filenames:

                        download_result = download_and_delete(path, filename, session)
                        if download_result:
                            os.system(f'spd-say "{counter}"')
                        else:
                            os.system('spd-say "an error has occurred"')
                        
                    unmount(usb_path)
                    os.system('spd-say "detach your card"')
                    start_processing_in_background(session)

                    logging.debug("Sleeping")

                except Exception as e:

                    logging.error(f"There's a problem processing '{usb_path}': {e}")

            logging.debug("Sleeping")
            time.sleep(10)  # poll every 10 seconds for active cards
                

    #execute this code if CTRL + C is used to kill python script
    except KeyboardInterrupt:

        print("Bye!")

    except Exception as e:

        logging.error(traceback.format_exc())
        # Logs the error appropriately.


def find_first_mounted_n2pdcim_usb_name():

    files = glob.glob(f"{_USB}/*/n2p")
    if files:
        usb_name = files[0].split('/')[-1]
        usb_path = files[0].split(usb_name)[0]
        logging.info(f"'{usb_name}' is mounted!")
        return usb_name, usb_path
    else:
        return None, None


def new_session_name():
    return datetime.datetime.now().strftime('%Y%m%d%H%M')


def get_list_of_filenames_on_camera(usb_path):
    # returning a list of tuples (path, filename)

    logging.info("Reading card...")
    list_of_filenames = []
    files = glob.glob(f"{usb_path}/DCIM/*/*.ARW")

    for file in files:

        filename = file.split('/')[-1]
        path = file.split(filename)[0]
        logging.debug(f"File on card: {file}")
        list_of_filenames.append((path, filename))

    logging.info(f"Retrieved a list of {len(list_of_filenames)} files that are on the card")
    return list_of_filenames


def download_and_delete(path, filename, session):
    # the file is downloaded and stored into
    # {_TEMP}/{session}/{filename}
    # and the original file is deleted
    file = f"{path}/{filename}"

    try:
        # download to {_TEMP}
        os.makedirs(f"{_TEMP}/{session}", exist_ok=True)
        dirpath = f"{_TEMP}/{session}"

        logging.info(f"Going to move {file}")
        sleep = 1
        for attempt in range(10):
            try:
                logging.info(f"Moving {file}")
                shutil.move(file, dirpath)
            except Exception as e:
                time.sleep(sleep)  # pause hoping things will normalize
                logging.warning(f"Sleeping {sleep} seconds because of error trying to move {file} ({e}).")
                sleep *= 2
            else:
                logging.info(f"Downloaded and deleted '{file}'")
                break  # no error caught
        else:
            logging.critical(f"Retried 10 times copying {file}")
        logging.info(f"Moved '{file}' to '{dirpath}'")
        return True
    except Exception as e:
        logging.error(f"Error downloading '{file}': {e}")
        logging.error(traceback.format_exc())
        return False



def unmount(usb_path):
    os.system(f"umount {usb_path}")
    logging.info(f"Unmounted {usb_path}")


def start_processing_in_background(session):
    subprocess.Popen(["/usr/bin/time", _N2P_], cwd=f"{_TEMP}/{session}")
    logging.info(f"Started n2p_2023 in the background in {_TEMP}/{session}")


if __name__ == "__main__":
    main()
