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
import sys

class TagServer:
    """
    Flask server for tagging images.

    Parameters
    ----------
    config_file : str
        Path the YAML configuration file.

    Methods
    -------
    start()
        Starts the Flask server.
    """

    def __init__(self, config_file):
        # Set up config and image services
        self._config = ConfigReader(config_file)
        self.loader = Loader(self._config)

        # Create Flask app and define routes
        self._app = Flask(__name__, static_url_path="/static")
        self._app.add_url_rule("/", "index", self.show_index)
        self._app.add_url_rule("/finished", "finished", self.finished)
        self._app.add_url_rule("/show_image/<index>", "show_image/<index>", self.show_image)
        self._app.add_url_rule(
            "/store_tags", "store_tags", self.store_tags, methods=["POST"]
        )
        print("rules added!")
        return

    def start(self):
        """Starts the Flask server with the configured host settings."""

        # Get config settings
        host = self._config.get("server/host", "127.0.0.1")
        port = self._config.get("server/port", "8080")
        debug = self._config.get("server/debug mode", True)
        host_str = f"http://{host}:{port}/"

        # The reloader has not yet run - open the browser
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            webbrowser.open_new(host_str)

        # Run Flask app
        #self._app.run(host=host, port=port, debug=debug, use_reloader=False)

    #@self.app.route("/")
    def show_index(self):
        """Routing: Show the main page."""
        print("showing main page")
        image_id = request.args.get("image_id")
        if not image_id:
            data = self.loader.next_data()
            if data is None:
                return redirect("/finished")
            return redirect(f"/?image_id={data['id']}")

        else:
            content = self._render_image(image_id)

        metadata = {
            "max_image_width": self._config.get("interface/max_width", 200),
            "max_image_height": self._config.get("interface/max_height", 200),
        }
        return render_template("index.html", content=content, meta=metadata)

    #@self._app.route("/finished")
    def finished(self):
        return render_template("finished.html")

    #@self._app.route("/show_image/<index>")
    def show_image(self, index):
        """Routing: Sends the image file to the webbrowser."""
        print("showing image")
        image_id = request.args.get("image_id")
        image = self.loader.get_by_id(image_id)
        zip_file_path = image["path"]
        folder_name = zip_file_path.split(".zip")[0].split("/")[-1]
        final_path = '/root/image_tagging/example_images/' + folder_name + '/' + str(index) + '.jpeg'
        with open('output.txt', 'w') as f:
            f.write(final_path)
            f.write("\n")
            f.write(folder_name)
        width = self._config.get("interface/max_width", 200)
        height = self._config.get("interface/max_height", 200)
        if not os.path.exists(final_path):
            path_to_dicoms = utils.unzip(zip_file_path)
            datasets = utils.read_patinet(path_to_dicoms)
            matrices = []
            dataset = datasets[int(index)]
            image_matrix = dataset.pixel_array
            matrices.append(image_matrix)
            image = Image.fromarray(image_matrix).convert('L')
            image = image.resize((width, height))
            if not os.path.exists('/root/image_tagging/example_images/' + folder_name):
                os.mkdir('/root/image_tagging/example_images/' + folder_name)
            image.save(final_path)
        return send_file(final_path, mimetype='image/jpg')

    #@self._app.route("/store_tags")
    def store_tags(self):
        """Routing: Stores the (updated) tag data for the image."""
        data = {
            "id": request.form.get("id"),
            "tag": request.form.get('tags'),
            "SHOWN": 0
        }
        print("storing tags")
        self.loader.store(data)

        next_image = self.loader.next_data()
        if next_image is None:
            return redirect("/finished")
        target = "/"
        if next_image:
            target = f"/?image_id={next_image['id']}"
        return redirect(location=target)

    def _render_image(self, image_id):
        """
        Renders image template for the provided image ID.

        Parameters
        ----------
        image_id : str
            MD5 hash for the image to render.
        """

        # Load all available tags from cofniguration
        shortcuts = self._config.get("tagging/tags")
        if not shortcuts:
            raise ValueError("Could not read any tags from the configuration file.")

        # Load and preprocess the data
        data = self.loader.get_by_id(image_id)
        remaining, count = self.loader.get_remaining_and_count()
        if not data:
            raise RuntimeError(f"Cannot render image with ID '{image_id}'.")
        data['remaining'] = remaining
        data['count'] = count
        # Add meta data
        data["all_tags"] = list(shortcuts)
        data["shortcuts"] = shortcuts
        data["tag_question"] = self._config.get("tagging/tag question", "Select tags:")
        data["allow_remarks"] = self._config.get("tagging/allow remarks", False)
        data["multi_select"] = self._config.get("tagging/multi-select", False)
        # print(self.loader.get_shown_images())
        return render_template("tag_image.html", **data)
