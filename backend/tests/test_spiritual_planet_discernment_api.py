from __future__ import annotations


def _payload() -> dict:
    return {
        "title": "公开成功叙事辨识",
        "subject_type": "media",
        "raw_input": "这段公开演讲反复声称，只有持续成功并获得关注，一个人才有价值。",
        "user_goal": "区分可观察主张、世界观候选与属灵假设",
        "faith_context": "christian",
        "sensitivity": "normal",
        "consent_scope": {
            "allow_spiritual_analysis": True,
            "allow_gospel_bridge": True,
            "allow_public_content_analysis": True,
            "allow_longitudinal_memory": False,
        },
        "source_metadata": {"platform": "public-web"},
        "source_items": [{
            "source_type": "public_reference",
            "locator": "https://example.test/public-talk",
            "evidence_level": "P1",
            "independence_group": "speaker-primary",
            "limitations": ["测试用公开定位"],
        }],
    }


def test_authenticated_api_persists_complete_discernment_workflow(client, auth_headers):
    catalog = client.get("/api/v1/platform/discernment/catalog", headers=auth_headers)
    assert catalog.status_code == 200
    assert catalog.json()["catalog"]["counts"]["domain_packs"] == 32

    created = client.post("/api/v1/platform/discernment/cases", json=_payload(), headers=auth_headers)
    assert created.status_code == 201, created.text
    case_id = created.json()["case"]["id"]
    assert created.json()["report"]["observed_claims"]

    listed = client.get("/api/v1/platform/discernment/cases", headers=auth_headers)
    assert listed.status_code == 200
    assert case_id in {item["id"] for item in listed.json()["cases"]}

    fetched = client.get(f"/api/v1/platform/discernment/cases/{case_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["input"]["source_items"][0]["evidence_level"] == "P1"

    reanalyzed = client.post(f"/api/v1/platform/discernment/cases/{case_id}/reanalyze", headers=auth_headers)
    assert reanalyzed.status_code == 200
    assert reanalyzed.json()["report"]["trace"][-1]["state"] in {"READY", "HUMAN_REVIEW_REQUIRED"}

    dialogue = client.post(
        f"/api/v1/platform/discernment/cases/{case_id}/dialogue",
        json={"preferred_depth": "standard"},
        headers=auth_headers,
    )
    assert dialogue.status_code == 201, dialogue.text
    session_id = dialogue.json()["session"]["session_id"]
    turn = client.post(
        f"/api/v1/platform/discernment/dialogues/{session_id}/turns",
        json={"answer": "我担心失败会使我失去他人的肯定。"},
        headers=auth_headers,
    )
    assert turn.status_code == 200, turn.text

    gospel = client.post(
        f"/api/v1/platform/discernment/cases/{case_id}/gospel-path",
        json={"preferred_depth": "standard", "church_context": "本地教会"},
        headers=auth_headers,
    )
    assert gospel.status_code == 200, gospel.text
    assert len(gospel.json()["gospel_path"]["segments"]) == 10

    review = client.post(
        f"/api/v1/platform/discernment/cases/{case_id}/reviews",
        json={"action": "REQUEST_REVIEW", "note": "请人工复核传播证据", "correction": {}},
        headers=auth_headers,
    )
    assert review.status_code == 201, review.text

    deleted = client.delete(f"/api/v1/platform/discernment/cases/{case_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "withdrawn"
    assert client.get(f"/api/v1/platform/discernment/cases/{case_id}", headers=auth_headers).status_code == 404
