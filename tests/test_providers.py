import pytest

from baseline.providers import prediction_json_schema, prediction_model


def test_prediction_models_match_family_shapes():
    assert prediction_model("flow").model_validate({"choice": "A"}).model_dump() == {"choice": "A"}
    assert prediction_model("gapnum").model_validate({"gap_px": 12}).model_dump() == {"gap_px": 12}
    assert prediction_model("headerpx").model_validate(
        {"above_px": 24, "below_px": 8}).model_dump() == {"above_px": 24, "below_px": 8}
    assert prediction_model("regionpx").model_validate({"pad_px": 16}).model_dump() == {"pad_px": 16}
    with pytest.raises(ValueError):
        prediction_model("nope")


def test_prediction_models_reject_wrong_shapes():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        prediction_model("flow").model_validate({"gap_px": 12})
    with pytest.raises(ValidationError):
        prediction_model("flow").model_validate({"choice": "A", "extra": 1})
    with pytest.raises(ValidationError):
        prediction_model("gapnum").model_validate({"gap_px": [12]})
    with pytest.raises(ValidationError):
        prediction_model("headerpx").model_validate({"above_px": 24})


def test_prediction_schemas_are_strict_compatible():
    for family in ("flow", "gapnum", "headerpx", "regionpx"):
        schema = prediction_json_schema(family)
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
