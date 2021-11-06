"""Module containing the Flask tagging server."""

import io
import os
import argparse
import webbrowser

from flask import Flask, render_template, request, redirect, send_file, Response

from config import ConfigReader
from dataset_loader import Loader
import utils
from PIL import Image

app = Flask(__name__, static_url_path="/static")
config = ConfigReader('example_config.yaml')
loader = Loader(config)


@app.route("/")
def show_index():
    """Routing: Show the main page."""

    image_id = request.args.get("image_id")
    if not image_id:
        data = loader.next_data()
        if data is None:
            return redirect("/finished")
        return redirect(f"/?image_id={data['id']}")

    else:
        content = _render_image(image_id)

    metadata = {
        "max_image_width": _config.get("interface/max_width", 200),
        "max_image_height": _config.get("interface/max_height", 200),
    }
    return render_template("index.html", content=content, meta=metadata)


@app.route("/finished")
def finished():
    return render_template("finished.html")


@app.route("/show_image/<index>")
def show_image(index):
    """Routing: Sends the image file to the webbrowser."""
    image_id = request.args.get("image_id")
    image = loader.get_by_id(image_id)
    zip_file_path = image["path"]
    folder_name = zip_file_path.split(".")[1].split("/")[-1]
    final_path = 'example_images/' + folder_name + '/' + str(index) + '.jpeg'
    width = _config.get("interface/max_width", 200)
    height = _config.get("interface/max_height", 200)
    if not os.path.exists(final_path):
        path_to_dicoms = utils.unzip(zip_file_path)
        datasets = utils.read_patinet(path_to_dicoms)
        matrices = []
        dataset = datasets[int(index)]
        image_matrix = dataset.pixel_array
        matrices.append(image_matrix)
        image = Image.fromarray(image_matrix).convert('L')
        image = image.resize((width, height))
        if not os.path.exists('example_images/' + folder_name):
            os.mkdir('example_images/' + folder_name)
        image.save(final_path)
    return send_file(final_path, mimetype='image/jpg')


@app.route("/store_tags")
def store_tags():
    """Routing: Stores the (updated) tag data for the image."""
    data = {
        "id": request.form.get("id"),
        "tag": request.form.get('tags'),
        "SHOWN": 0
    }
    loader.store(data)

    next_image = loader.next_data()
    if next_image is None:
        return redirect("/finished")
    target = "/"
    if next_image:
        target = f"/?image_id={next_image['id']}"
    return redirect(location=target)


def _render_image(image_id):
    """
    Renders image template for the provided image ID.

    Parameters
    ----------
    image_id : str
        MD5 hash for the image to render.
    """

    # Load all available tags from cofniguration
    shortcuts = config.get("tagging/tags")
    if not shortcuts:
        raise ValueError("Could not read any tags from the configuration file.")

    # Load and preprocess the data
    data = loader.get_by_id(image_id)
    remaining, count = loader.get_remainingand_count()
    if not data:
        raise RuntimeError(f"Cannot render image with ID '{image_id}'.")
    data['remaining'] = remaining
    data['count'] = count
    # Add meta data
    data["all_tags"] = list(shortcuts)
    data["shortcuts"] = shortcuts
    data["tag_question"] = config.get("tagging/tag question", "Select tags:")
    data["allow_remarks"] = config.get("tagging/allow remarks", False)
    data["multi_select"] = config.get("tagging/multi-select", False)
    # print(loader.get_shown_images())
    return render_template("tag_image.html", **data)


def init():
    # Create Flask app and define routes
    app.add_url_rule("/", "index", show_index)
    app.add_url_rule("/finished", "finished", finished)
    app.add_url_rule("/show_image/<index>", "show_image/<index>", show_image)
    app.add_url_rule(
        "/store_tags", "store_tags", store_tags, methods=["POST"]
    )
    return


init()
