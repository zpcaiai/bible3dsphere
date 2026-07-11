"""One transactional polling cycle; deployment scheduling stays outside domain."""
from typing import Any, Callable, Mapping
from .outbox import claim_batch,deliver,mark_failed,mark_published

def run_once(conn,handlers:dict[str,tuple[str,Callable[[Mapping[str,Any]],None]]],limit:int=50)->dict:
    result={"published":0,"retried":0,"dead_letter":0,"unhandled":0}
    with conn.cursor() as cur:
        for event in claim_batch(cur,limit):
            target=handlers.get(event.event_type)
            if not target:
                result["unhandled"]+=1;mark_failed(cur,event,LookupError(f"no consumer for {event.event_type}"));continue
            consumer,handler=target
            try:deliver(cur,event,consumer,handler);mark_published(cur,event.id);result["published"]+=1
            except Exception as exc:
                state=mark_failed(cur,event,exc);result["dead_letter" if state=="dead_letter" else "retried"]+=1
    conn.commit();return result
