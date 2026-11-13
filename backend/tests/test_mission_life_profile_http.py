"""Regression for the deployed Mission Life router over HTTP and PostgreSQL."""
import os

import httpx


def test_profile_summary_and_commitment_authority():
    base = os.environ["NATIVE_MISSION_LIFE_BASE_URL"]
    owner = {"Authorization": "Bearer " + os.environ["NATIVE_MISSION_LIFE_TOKEN"]}
    outsider = {"Authorization": "Bearer " + os.environ["NATIVE_MISSION_LIFE_OUTSIDER_TOKEN"]}
    with httpx.Client(base_url=base + "/api/mission-life", timeout=10) as client:
        summary = "Keep the actual adopted mission summary."
        created = client.post("/profiles", headers=owner, json={
            "life_season": "academic",
            "mission_summary": summary,
        })
        created.raise_for_status()
        profile = created.json()["profile"]
        assert profile["mission_summary"] == summary
        latest = client.get("/profiles/latest", headers=owner)
        latest.raise_for_status()
        assert latest.json()["profile"] == profile
        assert client.get("/profiles/latest", headers=outsider).json()["profile"] is None
        payload = {"domain_key": "learning_teaching", "title": "Practice teaching"}
        path = f"/profiles/{profile['id']}/commitments"
        assert client.post(path, json=payload).status_code == 401
        assert client.post(path, headers=outsider, json=payload).status_code == 404
        assert client.post("/profiles/unknown/commitments", headers=owner, json=payload).status_code == 404
        accepted = client.post(path, headers=owner, json=payload)
        accepted.raise_for_status()
        assert accepted.json()["commitment"]["profile_id"] == profile["id"]
        owner_list = client.get("/commitments", headers=owner)
        owner_list.raise_for_status()
        assert owner_list.json()["commitments"] == [accepted.json()["commitment"]]
        outsider_list = client.get("/commitments", headers=outsider)
        outsider_list.raise_for_status()
        assert outsider_list.json()["commitments"] == []
