# Processing a exposure device with settings
# Check if output already exists
# Create temp folder
# Copy code to temp folder
# slicing() -> images at px_size and layer_size
# 	check if in unique_component_index
# 		if not unique return else add to index
# 	union bulk
# 	subtract shapes
# 	_loop_components()
# 		if not exposure device
# 			if layer_size is equal
# 				_loop_components()
# 			else:
# 				slicing() in own directory
# 		else:
# 			slicing() in new directory
# 	slice at layer_size
# 		slice
# 		add to index of image_name and layer position
# 	If layers align, merge images
# Generate secondary and membrane images
# Generate JSON
# 	make minimal slices folder
# Create print job zip/directory
# Clean up temp folder

from datetime import datetime
from pathlib import Path

# from .secondary_image_generation import generate_secondary_images
# from .membrane_image_generation import generate_membrane_images
# from .generate_print_file import create_print_file
from ..backend import slice


class Slicer:
    def __init__(self, device, settings: dict, filename: str, zip_output: bool = False):
        """
        ###### Initialize the Slicer with a device and settings.

        ###### Parameters:
        - device: Device to be sliced.
        - settings: Slicer settings dictionary.
        - filename: Name of the output file.
        - zip_output: Whether to output as a zip file.
        """
        self.device = device
        self.settings = settings
        self.filename = filename
        self.zip_output = zip_output

    def check_output_exists(self, output_path: str) -> bool:
        """
        ###### Check if the output path already exists.

        ###### Parameters:
        - output_path: Path to check for existing output.

        ###### Returns:
        - True if output exists, False otherwise.
        """
        output_path = Path(output_path)
        if self.zip_output:
            return output_path.exists() and output_path.is_file()
        else:
            return output_path.exists() and output_path.is_dir()

    def generate_temp_directory(self) -> Path:
        """
        Generate a temporary directory for processing.

        :return: Path to the temporary directory.
        """
        temp_directory = Path(f"tmp_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        temp_directory.mkdir(parents=True, exist_ok=True)
        return temp_directory

    def make_print_file(self):
        """
        Generate a print file based on the provided device and settings.
        This function will create a temporary directory, slice the device's components,
        generate secondary and membrane images, create a JSON file with the print data,
        and create a print job zip or directory.
        """

        # Check if output already exists
        if self.check_output_exists(self.filename):
            print(
                f"Output already exists at {self.filename}. Please select a different path."
            )
            return False

        # Create a temporary directory for processing
        temp_directory = self.generate_temp_directory()

        # Copy code to the temporary directory
        #### TODO: Implement code copying logic if needed

        # try:
        # Slice the device components
        sliced_devices = []
        sliced_devices_info = []
        slice(self.device, temp_directory, sliced_devices, sliced_devices_info)

        # # Generate secondary images
        # generate_secondary_images(device, temp_directory, slicer_settings)

        # # Generate membrane images
        # generate_membrane_images(device, temp_directory, slicer_settings)

        # # Create the print file JSON
        # create_print_file(
        #     output_path,
        #     device,
        #     temp_directory,
        #     slicer_settings=slicer_settings,
        #     zip_output=zip_output,
        # )

        # finally:
        #     # Clean up the temporary directory
        #     if temp_directory.exists():
        #         for item in temp_directory.iterdir():
        #             if item.is_dir():
        #                 item.rmdir()
        #             else:
        #                item.unlink()
        #        temp_directory.rmdir()
