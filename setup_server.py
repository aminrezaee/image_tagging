import os
import utils
from PIL import Image
from config import ConfigReader
# creating jpegs from zip of dicom files for better and faster image displaying
zip_files_path = '/root/prostate_diagnosis/prostate_diagnosis/images_without_label/'
config = ConfigReader('example_config.yaml')
width = config.get("interface/max_width", 200)
height = config.get("interface/max_height", 200)


def extract_zips():
    zip_files = os.listdir(zip_files_path)
    for j in range(len(zip_files)):
        file = zip_files[j]
        path_to_dicoms = utils.unzip(zip_files_path + file)
        folder_name = file.split(".zip")[0]
        datasets = utils.read_patinet(path_to_dicoms)
        for i in range(len(datasets)):
            if not os.path.exists('static/example_images/' + folder_name + "/" + str(i) + '.jpeg'):
                final_path = 'static/example_images/' + folder_name + '/' + str(i) + '.jpeg'
                dataset = datasets[i]
                image_matrix = dataset.pixel_array
                image = Image.fromarray(image_matrix).convert('L')
                image = image.resize((width, height))
                if not os.path.exists('static/example_images/' + folder_name):
                    os.mkdir('static/example_images/' + folder_name)
                image.save(final_path)
        print(j)
    return


extract_zips()
