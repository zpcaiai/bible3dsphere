from __future__ import annotations
import os
import psycopg

PROGRAMS=('local-leader-90','attention-reset-30','ai-faith-dialogue-8','driver-audio-7','caregiver-support','church-harm-recovery')
def main():
 url=os.getenv('DATABASE_URL')
 if not url:raise SystemExit('DATABASE_URL is required')
 with psycopg.connect(url) as conn,conn.cursor() as cur:
  cur.execute("SELECT id FROM mission_bridge_program_definitions WHERE id=ANY(%s)",(list(PROGRAMS),));found={r[0] for r in cur.fetchall()};missing=set(PROGRAMS)-found
  if missing:raise SystemExit(f'run migrations first; missing programs: {sorted(missing)}')
  cur.execute("INSERT INTO mission_bridge_micro_audio(tenant_id,title,duration_minutes,audio_url,topic,published) VALUES('public','司机七分钟同行示例',7,'/mission-audio/driver-7-demo.mp3','压力与家庭沟通',FALSE) ON CONFLICT DO NOTHING")
  conn.commit()
 print(f'MissionBridge seed verified: {len(PROGRAMS)} programs')
if __name__=='__main__':main()
