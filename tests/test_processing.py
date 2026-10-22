"""Tests for the earthquake processing pipeline."""

from src.processing import process_events


def test_processed_dataset_has_unique_event_ids():
    df = process_events()
    assert df["event_id"].is_unique


def test_processed_dataset_has_expected_columns():
    df = process_events()

    expected_columns = {
        "event_id",
        "event_time",
        "magnitude",
        "place",
        "longitude",
        "latitude",
        "depth_km",
        "negative_depth_flag",
        "magnitude_type",
        "status",
        "tsunami",
        "felt_reports",
        "significance",
    }

    assert expected_columns.issubset(set(df.columns))


def test_negative_depth_flag_matches_depth_values():
    df = process_events()
    expected = df["depth_km"] < 0

    assert (df["negative_depth_flag"] == expected).all()


def test_magnitudes_meet_extraction_threshold():
    df = process_events()
    assert (df["magnitude"] >= 2.5).all()


def test_coordinates_are_within_valid_ranges():
    df = process_events()

    assert df["longitude"].between(-180, 180).all()
    assert df["latitude"].between(-90, 90).all()


def test_event_timestamps_are_present():
    df = process_events()
    assert df["event_time"].notna().all()
