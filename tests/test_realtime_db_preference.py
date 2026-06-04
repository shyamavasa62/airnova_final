from __future__ import annotations

import io


def test_realtime_cities_uses_db_after_ingest(client):
    csv = (
        "City,Date,AQI,PM2.5,PM10,NO2,SO2,CO,O3\n"
        "Delhi,01/01/18,120,55,110,22,6,1.2,18\n"
        "Bengaluru,01/01/18,80,30,70,12,4,0.7,10\n"
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

    cres = client.get("/realtime/cities")
    assert cres.status_code == 200
    cities = cres.get_json()["cities"]
    assert "Delhi" in cities
    assert "Bengaluru" in cities

