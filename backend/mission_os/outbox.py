"""Transactional Outbox repository and idempotent consumer primitives."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

SENSITIVE_KEYS=frozenset({"reflection","summary","narrative","passport","token","exact_location","local_contact","mental_health_text"})
MAX_ATTEMPTS=8

def _assert_redacted(value:Any,path:str="payload")->None:
    if isinstance(value,Mapping):
        for key,item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:raise ValueError(f"sensitive field forbidden in outbox: {path}.{key}")
            _assert_redacted(item,f"{path}.{key}")
    elif isinstance(value,list):
        for index,item in enumerate(value):_assert_redacted(item,f"{path}[{index}]")

def enqueue(cur,*,tenant_id:str,aggregate_type:str,aggregate_id:str,event_type:str,event_version:int,
            actor_id:str,correlation_id:str,data:Mapping[str,Any],causation_id:str|None=None,event_id:str|None=None)->str:
    """Write using the caller's cursor so the event shares the business transaction."""
    if event_version<1:raise ValueError("event_version must be positive")
    _assert_redacted(data)
    eid=event_id or str(uuid.uuid4())
    payload={"event_id":eid,"event_type":event_type,"event_version":event_version,"tenant_id":tenant_id,
             "occurred_at":datetime.now(timezone.utc).isoformat(),"actor_id":actor_id,"aggregate_id":aggregate_id,
             "correlation_id":correlation_id,"data":dict(data)}
    cur.execute("INSERT INTO mission_outbox_events(id,tenant_id,aggregate_type,aggregate_id,event_type,event_version,payload,correlation_id,causation_id) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)",
                (eid,tenant_id,aggregate_type,aggregate_id,event_type,event_version,json.dumps(payload,separators=(",",":")),correlation_id,causation_id))
    return eid

@dataclass(frozen=True)
class OutboxEvent:
    id:str; tenant_id:str; event_type:str; payload:Mapping[str,Any]; attempts:int

def claim_batch(cur,limit:int=50)->list[OutboxEvent]:
    cur.execute("SELECT id,tenant_id,event_type,payload,attempts FROM mission_outbox_events WHERE published_at IS NULL AND next_attempt_at<=now() AND NOT EXISTS(SELECT 1 FROM mission_dead_letter_events d WHERE d.event_id=mission_outbox_events.id) ORDER BY occurred_at FOR UPDATE SKIP LOCKED LIMIT %s",(min(max(limit,1),200),))
    return [OutboxEvent(str(r[0]),r[1],r[2],r[3],r[4]) for r in cur.fetchall()]

def deliver(cur,event:OutboxEvent,consumer_key:str,handler:Callable[[Mapping[str,Any]],None])->str:
    cur.execute("SELECT status FROM mission_event_deliveries WHERE consumer_key=%s AND event_id=%s",(consumer_key,event.id)); row=cur.fetchone()
    if row and row[0]=="completed":return "duplicate"
    cur.execute("INSERT INTO mission_event_deliveries(consumer_key,event_id,status,attempts) VALUES(%s,%s,'processing',1) ON CONFLICT(consumer_key,event_id) DO UPDATE SET status='processing',attempts=mission_event_deliveries.attempts+1,updated_at=now()",(consumer_key,event.id))
    handler(event.payload)
    cur.execute("UPDATE mission_event_deliveries SET status='completed',completed_at=now(),last_error=NULL,updated_at=now() WHERE consumer_key=%s AND event_id=%s",(consumer_key,event.id))
    return "completed"

def mark_published(cur,event_id:str)->None:
    cur.execute("UPDATE mission_outbox_events SET published_at=now(),last_error=NULL,updated_at=now() WHERE id=%s",(event_id,))

def mark_failed(cur,event:OutboxEvent,error:Exception)->str:
    # Exception messages may contain tokens, contact details or narrative text.
    attempts=event.attempts+1; message=type(error).__name__
    if attempts>=MAX_ATTEMPTS:
        cur.execute("UPDATE mission_outbox_events SET attempts=%s,last_error=%s,updated_at=now() WHERE id=%s",(attempts,message,event.id))
        cur.execute("INSERT INTO mission_dead_letter_events(event_id,reason) VALUES(%s,%s) ON CONFLICT(event_id) DO UPDATE SET reason=EXCLUDED.reason,failed_at=now()",(event.id,message));return "dead_letter"
    delay=min(3600,2**attempts)
    cur.execute("UPDATE mission_outbox_events SET attempts=%s,last_error=%s,next_attempt_at=now()+(%s*interval '1 second'),updated_at=now() WHERE id=%s",(attempts,message,delay,event.id));return "retry"
