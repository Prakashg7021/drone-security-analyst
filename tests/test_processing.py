from drone_security.processing import extract_description


def test_extracts_person_vehicle_and_location():
    result = extract_description("Blue Ford F150 spotted at main gate.")
    assert result["location"] == "main gate"
    assert result["event_type"] == "vehicle"
    assert result["objects"] == [
        {
            "type": "vehicle",
            "label": "Ford F150",
            "kind": "truck",
            "color": "blue",
            "identity": "blue ford f150",
        }
    ]


def test_extracts_person_and_restricted_entry():
    result = extract_description("Person entering the restricted zone near east fence.")
    assert result["event_type"] == "restricted_area"
    assert result["activity"] == "entry"
    assert result["location"] == "east fence"
    assert result["objects"][0]["type"] == "person"
