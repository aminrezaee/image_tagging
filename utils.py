import os


def get_errored_samples(downloaded_path, current_ids):
    downloaded_image_ids = os.listdir(downloaded_path)
    errored = []
    for i in range(len(current_ids)):
        if not current_ids[i] + ".zip" in downloaded_image_ids:
            errored.append(current_ids)
    return errored


import zipfile
from zipfile import BadZipfile
import os
from pydicom import dcmread
import pydicom
import glob

from pathlib import Path


def read_patinet(path):
    dicoms = []
    for path in Path(path).rglob('*.dcm'):
        full_path = str(path.parent) + '/' + str(path.name)
        print("ok")
        dicoms.append(pydicom.filereader.dcmread(full_path))
        if len(dicoms) > 4:
            break
    return dicoms


def myprint(dataset, indent=0):
    """Go through all items in the dataset and print them with custom format

    Modelled after Dataset._pretty_str()
    """
    dont_print = ['Pixel Data', 'File Meta Information Version']

    indent_string = "   " * indent
    next_indent_string = "   " * (indent + 1)

    for data_element in dataset:
        if data_element.VR == "SQ":  # a sequence
            print(indent_string, data_element.name)
            for sequence_item in data_element.value:
                myprint(sequence_item, indent + 1)
                print(next_indent_string + "---------")
        else:
            if data_element.name in dont_print:
                print("""<item not printed -- in the "don't print" list>""")
            else:
                repr_value = repr(data_element.value)
                if len(repr_value) > 50:
                    repr_value = repr_value[:50] + "..."
                print("{0:s} {1:s} = {2:s}".format(indent_string,
                                                   data_element.name,
                                                   repr_value))


def check_modality(dataset):
    modality = dataset['Modality'].repval.replace("'", "")
    # print(modality)
    if modality.__contains__('MR') or modality.__contains__('OT'):
        return True
    print("bad modality")
    return False


body_part_string = "BodyPartExamined"


def check_body_part(dataset):
    if body_part_string in dataset:
        body_part = dataset[body_part_string].repval.replace("'", "")
        if "prostate" not in body_part.lower():
            print(body_part)
            return False
    return True


def unzip(path, required_path='temp/'):
    try:
        file_reference = zipfile.ZipFile(path, 'r')
        required_directory_name = path.split(".")[1].split("/")[-1]
        if not os.path.exists(required_path + required_directory_name):
            os.mkdir(required_path + required_directory_name)
            file_reference.extractall(required_path + required_directory_name)
    except BadZipfile:
        print("bad zip file")
        return None
    return required_path + required_directory_name


import shutil


def move_file(path_to_file):
    shutil.move(path_to_file, "not_prostate/")
    return


def remove_directory(path_to_file):
    shutil.rmtree(path_to_file)
    return


def start():
    images_path = '/home/ubuntu/project/prostate_diagnosis/images_without_label/'
    count = 0
    file_list = os.listdir(images_path)
    for file in file_list:
        if '.zip' not in file:
            remove_directory(images_path + file)
            count += 1
            print("directory_removed")
    print(count)
    file_list = os.listdir(images_path)
    count = 0
    for file_name in file_list:
        count += 1
        required_directory_path = unzip(file_name, images_path)
        # print(required_directory_path)
        if required_directory_path is None:
            continue
        dataset = read_patinet(required_directory_path + "/")
        if dataset is None:
            print("none")
            remove_directory(required_directory_path)
            continue
        is_good = check_modality(dataset)
        if is_good:
            is_good = check_body_part(dataset)
        print("removing directory")
        remove_directory(required_directory_path)
        if not is_good:
            move_file(images_path + file_name)
            print("data removed!")
            print(count)
    print(count)
    return


def dicom_to_pix_array(dicom):
    image = dicom.pixel_array
    return image
