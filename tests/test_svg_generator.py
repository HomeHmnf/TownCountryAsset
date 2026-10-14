import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from tools.generate_country_svgs import generate_svgs, geometry_to_svg


def polygon_with_hole():
    return {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
            [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]],
        ],
    }


def test_svg_generation_preserves_hole_and_fits_viewbox():
    svg = geometry_to_svg(polygon_with_hole())
    root = ET.fromstring(svg)
    assert root.attrib["viewBox"] == "0 0 512 512"
    assert root.attrib["width"] == "512"
    path = root.find("{http://www.w3.org/2000/svg}path")
    assert path is not None
    assert path.attrib["fill-rule"] == "evenodd"
    assert path.attrib["d"].count("M") == 2
    assert path.attrib["d"].count("Z") == 2


def test_svg_generation_supports_multipolygon():
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]],
            [[[5, 5], [5, 7], [7, 7], [7, 5], [5, 5]]],
        ],
    }
    root = ET.fromstring(geometry_to_svg(geometry))
    path = root.find("{http://www.w3.org/2000/svg}path")
    assert path is not None
    assert path.attrib["d"].count("M") == 2


@pytest.mark.parametrize("geometry", [
    {"type": "Point", "coordinates": [0, 0]},
    {"type": "Polygon", "coordinates": []},
])
def test_svg_generation_rejects_unsupported_or_empty_geometry(geometry):
    with pytest.raises(ValueError):
        geometry_to_svg(geometry)


def test_generate_svgs_for_each_profile(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "countries.json").write_text(json.dumps({
        "countries": [{"id": "TST", "name": "Testland"}]
    }), encoding="utf-8")
    for profile in ("low", "medium", "high"):
        (data / f"geometry_{profile}.json").write_text(json.dumps({
            "profile": profile,
            "geometries": {"TST": polygon_with_hole()},
        }), encoding="utf-8")

    output = tmp_path / "svg"
    assert generate_svgs(data, output) == 3
    for profile in ("low", "medium", "high"):
        svg_file = output / profile / "TST.svg"
        assert svg_file.is_file()
        assert ET.parse(svg_file).getroot().attrib["viewBox"] == "0 0 512 512"
