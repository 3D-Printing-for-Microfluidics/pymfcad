from pymfcad import ExposureSettings, LightEngine, PositionSettings, Printer

HR3v3 = Printer(
    name="HR3v3",
    light_engines=[
        LightEngine(
            name="visitech",
            px_size=0.0076,
            px_count=(2560, 1600),
            wavelengths=[365],
            default_exposure_settings=[
                ExposureSettings(
                    grayscale_correction=True,
                    bulk_exposure_multiplier=1.0,
                    power_setting=100,
                    wavelength=365,
                ),
            ],
            grayscale_available=[True],
            settle_time_ms=0.0,
            stitched_px_overlap=(0, 0),
            x_offset_limits=(-9728, 9728),
            y_offset_limits=(-6080, 6080),
        ),
    ],
    xy_stage_available=False,
    vacuum_available=False,
    default_position_settings=PositionSettings(),
)

OS1v0 = Printer(
    name="OS1v0",
    light_engines=[
        LightEngine(
            name="visitech",
            px_size=0.0076,
            px_count=(2560, 1600),
            wavelengths=[365],
            default_exposure_settings=[
                ExposureSettings(
                    grayscale_correction=True,
                    bulk_exposure_multiplier=1.0,
                    power_setting=100,
                    wavelength=365,
                ),
            ],
            grayscale_available=[True],
            settle_time_ms=0.0,
            stitched_px_overlap=(0, 0),
            x_offset_limits=(-9728, 9728),
            y_offset_limits=(-6080, 6080),
        ),
    ],
    xy_stage_available=True,
    vacuum_available=False,
    default_position_settings=PositionSettings(),
)

HR5 = Printer(
    name="HR5",
    light_engines=[
        LightEngine(
            name="visitech",
            px_size=0.0076,
            px_count=(2560, 1600),
            wavelengths=[365],
            default_exposure_settings=[
                ExposureSettings(
                    grayscale_correction=True,
                    bulk_exposure_multiplier=1.0,
                    power_setting=100,
                    wavelength=365,
                ),
            ],
            grayscale_available=[True],
            settle_time_ms=0.0,
            stitched_px_overlap=(0, 0),
            x_offset_limits=(-9728, 9728),
            y_offset_limits=(-6080, 6080),
        ),
    ],
    xy_stage_available=True,
    vacuum_available=True,
    default_position_settings=PositionSettings(),
)

MR1v1 = Printer(
    name="MR1v1",
    light_engines=[
        LightEngine(
            name="visitech",
            px_size=0.0152,
            px_count=(2560, 1600),
            wavelengths=[405, 365],
            default_exposure_settings=[
                ExposureSettings(
                    bulk_exposure_multiplier=10.0,
                    power_setting=300,
                    wavelength=405,
                ),
                ExposureSettings(
                    bulk_exposure_multiplier=10.0,
                    power_setting=300,
                    wavelength=365,
                ),
            ],
            grayscale_available=[False, False],
            settle_time_ms=0.0,
            stitched_px_overlap=(0, 0),
            x_offset_limits=(-10000, 10000),
            y_offset_limits=(-10000, 10000),
        ),
        LightEngine(
            name="wintech",
            px_size=0.00075,
            px_count=(1920, 1080),
            wavelengths=[365],
            default_exposure_settings=[
                ExposureSettings(
                    bulk_exposure_multiplier=1.0,
                    power_setting=60,
                    wavelength=365,
                )
            ],
            grayscale_available=[False],
            settle_time_ms=2000.0,
            stitched_px_overlap=(0, 0),
            x_offset_limits=(-20000, 20000),
            y_offset_limits=(-50000, 50000),
        ),
    ],
    xy_stage_available=True,
    vacuum_available=False,
    default_position_settings=PositionSettings(),
)
