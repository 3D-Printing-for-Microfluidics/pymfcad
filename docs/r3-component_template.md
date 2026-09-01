Prev: [Part 10: Designing Custom Subcomponents](8-making_subcomponent.md)

```python

# import classes from pymfcad

# import components from custom classes or pymfcad.component_library

class ***MyComponent***(***Component or VariableLayerThicknessComponent***):
    def __init__(self, ***component_parameters***, quiet = False):

        # Initialize the base Component
        super().__init__(
            size=#component size tuple
            px_size=#component pixel size
            layer_size=#component layer size
            quiet=quiet
        )

		# Add slicing settings (bulk exposure, default settings, etc)

		# Add labels

        # Add voids

		# Add regional settings

		# Add bulk

		# Add ports

if __name__ == "__main__":
    ***MyComponent***().preview()

```