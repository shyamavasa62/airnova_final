from __future__ import annotations

import io
import time


def test_admin_retrain_trains_rf_and_arima(client):
    # Provide enough rows for RF training (needs >= 30 after shift)
    header = "City,Date,AQI,PM2.5,PM10,NO2,SO2,CO,O3\n"
    rows = []
    # Use unique dates to avoid heavy row drops during parsing/cleaning.
    for i in range(90):
        day = (i % 28) + 1
        month = (i // 28) + 1  # 1..4
        rows.append(f"Delhi,{day:02d}/{month:02d}/18,{100 + (i % 20)},55,110,22,6,1.2,18\n")
    csv = header + "".join(rows)

    res = client.post(
        "/admin/ingest",
        data={"mode": "replace", "file": (io.BytesIO(csv.encode("utf-8")), "dataset.csv")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200

    start = client.post("/admin/retrain")
    assert start.status_code == 202

    # Poll for completion (should be quick on small dataset)
    last = None
    for _ in range(30):
        st = client.get("/admin/retrain/status")
        assert st.status_code == 200
        last = st.get_json()
        if not last["running"]:
            break
        time.sleep(0.2)

    assert last is not None
    assert last["running"] is False
    assert last["last_error"] is None
    assert "random_forest" in last["last_result"]
    assert "arima" in last["last_result"]

