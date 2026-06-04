from __future__ import annotations

import io


def test_admin_ingest_replace_and_stats(client):
    csv = (
        "City,Date,AQI,PM2.5,PM10,NO2,SO2,CO,O3\n"
        "Delhi,01/01/18,120,55,110,22,6,1.2,18\n"
        "Delhi,02/01/18,130,60,115,24,7,1.1,20\n"
        "Mumbai,01/01/18,90,40,90,18,5,0.9,15\n"
    )

    res = client.post(
        "/admin/ingest",
        data={
            "mode": "replace",
            "file": (io.BytesIO(csv.encode("utf-8")), "dataset.csv"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["mode"] == "replace"
    assert body["inserted"] == 3
    assert body["db_rows"] == 3

    sres = client.get("/admin/stats")
    assert sres.status_code == 200
    sb = sres.get_json()
    assert sb["db_rows"] == 3


def test_admin_ingest_missing_columns(client):
    csv = "City,Date,AQI\nDelhi,01/01/18,120\n"
    res = client.post(
        "/admin/ingest",
        data={"mode": "replace", "file": (io.BytesIO(csv.encode("utf-8")), "bad.csv")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"]
    assert "missing" in body

