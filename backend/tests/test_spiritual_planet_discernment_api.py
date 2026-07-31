from __future__ import annotations

from datetime import datetime, timedelta, timezone


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
            "allow_longitudinal_memory": True,
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

    occurred_at = datetime.now(timezone.utc).isoformat()
    formation = client.post(
        "/api/v1/platform/discernment/formation/events",
        json={
            "case_id": case_id,
            "occurred_at": occurred_at,
            "context": "工作中的公开汇报",
            "trigger": "收到批评",
            "automatic_interpretation": "失败就等于我没有价值",
            "desire_or_fear": ["害怕失去认可"],
            "active_belief": ["必须表现完美"],
            "emotion": ["焦虑"],
            "body_signal": ["肩颈紧绷"],
            "chosen_action": ["先倾听再回应"],
            "relationship_effect": ["避免防御性反击"],
            "gospel_truth_recalled": ["接纳不是靠表现赚取"],
            "repair_action": ["向同事确认我听到的意见"],
            "outcome": "完成了较平稳的回应",
            "source_type": "self_report",
            "evidence_quality": "E2",
            "data_level": "L1",
            "consent_to_tracking": True,
        },
        headers=auth_headers,
    )
    assert formation.status_code == 201, formation.text
    event_id = formation.json()["event_id"]

    corrected = client.post(
        f"/api/v1/platform/discernment/formation/events/{event_id}/corrections",
        json={
            "case_id": case_id,
            "occurred_at": occurred_at,
            "context": "工作中的公开汇报",
            "trigger": "收到具体修改建议",
            "automatic_interpretation": "我需要核对证据，不把建议等同于身份否定",
            "chosen_action": ["记录建议并澄清优先级"],
            "outcome": "修正原记录的触发描述",
            "source_type": "self_report",
            "evidence_quality": "E2",
            "data_level": "L1",
            "consent_to_tracking": True,
        },
        headers=auth_headers,
    )
    assert corrected.status_code == 201, corrected.text

    snapshot = client.post("/api/v1/platform/discernment/formation/snapshot", headers=auth_headers)
    assert snapshot.status_code == 201, snapshot.text
    assert snapshot.json()["snapshot"]["quality_gates"]["no_single_maturity_score"] is True
    window = client.post(
        "/api/v1/platform/discernment/formation/reviews",
        json={"window_days": 14},
        headers=auth_headers,
    )
    assert window.status_code == 201, window.text
    assert window.json()["review"]["no_salvation_inference"] is True

    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    consent = client.post(
        "/api/v1/platform/discernment/collaboration/consents",
        json={
            "recipient_email": "pastor@example.test",
            "recipient_role": "mentor_discipler",
            "purpose": "预备一次同行复盘",
            "allowed_categories": ["L0", "L1"],
            "allowed_actions": ["view", "meeting_prep"],
            "expires_at": expires_at,
            "reshare_allowed": False,
        },
        headers=auth_headers,
    )
    assert consent.status_code == 201, consent.text
    consent_id = consent.json()["consent"]["id"]
    disclosure = client.post(
        "/api/v1/platform/discernment/collaboration/disclosures",
        json={
            "consent_id": consent_id,
            "case_id": case_id,
            "purpose": "预备一次同行复盘",
            "requested_fields": ["user_goal", "priority_question", "full_dialogue"],
            "data_level": "L1",
            "expires_at": expires_at,
        },
        headers=auth_headers,
    )
    assert disclosure.status_code == 201, disclosure.text
    assert "full_dialogue" in disclosure.json()["disclosure"]["redacted_fields"]
    meeting = client.post(
        "/api/v1/platform/discernment/collaboration/meeting-preps",
        json={
            "consent_id": consent_id,
            "case_id": case_id,
            "meeting_purpose": "预备一次同行复盘",
            "user_selected_focus": ["批评触发下的身份反应"],
            "last_agreements": ["先复述事实再回应"],
            "uncertainties": ["跨场景证据仍有限"],
            "priority_question": "怎样在压力中练习不靠表现定义自己？",
            "gospel_truth": "接纳不是靠表现赚取",
            "action_option": "下次汇报前写下一个澄清问题",
            "do_not_use_language": ["你就是骄傲"],
        },
        headers=auth_headers,
    )
    assert meeting.status_code == 201, meeting.text
    audit = client.get("/api/v1/platform/discernment/collaboration/audit", headers=auth_headers)
    assert audit.status_code == 200
    assert {item["action"] for item in audit.json()["audit"]} >= {"CONSENT_GRANTED", "DISCLOSURE_CREATED"}

    source = client.post(
        "/api/v1/platform/discernment/theology/sources",
        json={
            "title": "Public-domain Scripture Test Source",
            "source_type": "scripture",
            "language": "en",
            "rights_status": "public_domain",
            "version": "test-1",
            "author": [],
            "edition": "Public Domain Test Edition",
            "publisher": "Test fixture",
            "year": "1901",
            "quality_tier": "Q3",
            "limitations": ["Integration-test metadata only"],
            "user_confirms_rights": False,
        },
        headers=auth_headers,
    )
    assert source.status_code == 201, source.text
    source_id = source.json()["source"]["source_id"]
    theology = client.post(
        "/api/v1/platform/discernment/theology/queries",
        json={
            "question": "Romans 8:1 在段落和整卷书语境中如何理解？",
            "intent": "scripture_exegesis",
            "source_ids": [source_id],
            "citations": [{
                "source_id": source_id,
                "locator": "Romans 8:1",
                "quote_text": "There is therefore now no condemnation...",
                "extraction_method": "manual",
                "verification_status": "human_verified",
                "limitations": ["Short test quotation"],
            }],
            "allowed_rights": ["public_domain"],
            "required_source_types": ["scripture"],
            "scripture_refs": ["Romans 8:1"],
            "scripture_context": {
                "paragraph": "Romans 8:1-4",
                "book": "Romans",
                "genre": "epistle",
                "speaker": "Paul",
                "audience": "the church in Rome",
            },
            "tradition_scope": ["integration-test-unspecified-christian"],
            "doctrine_tier": "D3",
            "consensus_level": "open_question",
        },
        headers=auth_headers,
    )
    assert theology.status_code == 201, theology.text
    assert theology.json()["query"]["answer_status"] == "evidence_ready"
    assert theology.json()["query"]["evidence_graph"]["generated_statements"]

    certification = client.get("/api/v1/platform/discernment/certification/status", headers=auth_headers)
    assert certification.status_code == 200
    assert certification.json()["status"]["status"] == "NOT_EVALUATED"
    assert certification.json()["catalog"] == {"domains": 12, "controls": 58, "version": "1.0.0"}

    exported = client.get("/api/v1/platform/discernment/data-export", headers=auth_headers)
    assert exported.status_code == 200, exported.text
    assert len(exported.json()["export"]["formation_events"]) == 2
    assert {item["status"] for item in exported.json()["export"]["formation_events"]} == {"ACTIVE", "CORRECTED"}
    assert len(exported.json()["export"]["theology_queries"]) == 1

    erased = client.delete("/api/v1/platform/discernment/extended-data", headers=auth_headers)
    assert erased.status_code == 200, erased.text
    assert erased.json()["status"] == "DELETED"

    deleted = client.delete(f"/api/v1/platform/discernment/cases/{case_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "withdrawn"
    assert client.get(f"/api/v1/platform/discernment/cases/{case_id}", headers=auth_headers).status_code == 404
