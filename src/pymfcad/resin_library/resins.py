from pymfcad import ResinType

NPS = ResinType(
    bulk_exposure = 450,
    exposure_offset = 0.0,
    monomer = [("PEG", 100)],
    uv_absorbers = [("NPS", 2.0)],
    initiators = [("IRG", 1.0)],
    additives = [],
)

AVO = ResinType(
    bulk_exposure = 300,
    exposure_offset = 0.0,
    monomer = [("PEG", 100)],
    uv_absorbers = [("AVO", 0.42)],
    initiators = [("IRG", 1.0)],
    additives = [],
)

AVO_TPO = ResinType(
    bulk_exposure = 400,
    exposure_offset = 0.0,
    monomer = [("PEG", 100)],
    uv_absorbers = [("AVO", 0.42)],
    initiators = [("TPO", 1.0)],
    additives = [],
)

NPS_w_1_percent_crosslinker = ResinType(
    bulk_exposure = 650,
    exposure_offset = 0.0,
    monomer = [("PEG", 99), ("DTMPTA", 1)],
    uv_absorbers = [("NPS", 2.0)],
    initiators = [("IRG", 1.0)],
    additives = [("TEMPOL", 0.02)],
)

AVO_w_1_percent_crosslinker = ResinType(
    bulk_exposure = 500,
    exposure_offset = 0.0,
    monomer = [("PEG", 99), ("DTMPTA", 1)],
    uv_absorbers = [("AVO", 0.42)],
    initiators = [("IRG", 1.0)],
    additives = [("TEMPOL", 0.02)],
)

AVO_TPO_w_1_percent_crosslinker = ResinType(
    bulk_exposure = 900,
    exposure_offset = 0.0,
    monomer = [("PEG", 99), ("DTMPTA", 1)],
    uv_absorbers = [("AVO", 0.42)],
    initiators = [("TPO", 1.0)],
    additives = [("TEMPOL", 0.02)],
)

NPS_w_10_percent_crosslinker = ResinType(
    bulk_exposure = 900,
    exposure_offset = 0.0,
    monomer = [("PEG", 90), ("DTMPTA", 10)],
    uv_absorbers = [("NPS", 2.0)],
    initiators = [("IRG", 1.0)],
    additives = [("TEMPOL", 0.02)],
)

AVO_w_10_percent_crosslinker = ResinType(
    bulk_exposure = 900,
    exposure_offset = 0.0,
    monomer = [("PEG", 90), ("DTMPTA", 10)],
    uv_absorbers = [("AVO", 0.42)],
    initiators = [("IRG", 1.0)],
    additives = [("TEMPOL", 0.02)],
)

AVO_TPO_w_10_percent_crosslinker = ResinType(
    bulk_exposure = 900,
    exposure_offset = 0.0,
    monomer = [("PEG", 90), ("DTMPTA", 10)],
    uv_absorbers = [("AVO", 0.42)],
    initiators = [("TPO", 1.0)],
    additives = [("TEMPOL", 0.02)],
)
