# -*- coding: utf-8 -*-
"""Merge English fields into cards: python apply_en.py <module_with_EN_dict>
Sets lesson_en/summary_en/witness_en/prayer_en/follow_en/caution_en/applications_en by name."""
import json, subprocess, sys, importlib
MD="/sessions/exciting-determined-rubin/mnt/bible3dsphere-frontend/src/mirrorData.js"
EN=importlib.import_module(sys.argv[1]).EN
NODE="import('file://%s').then(m=>console.log(JSON.stringify(m.MIRROR_CHARACTERS)));"%MD
cards=json.loads(subprocess.check_output(["node","--input-type=module","-e",NODE]).decode())
names=set(c["name"] for c in cards)
miss=[n for n in EN if n not in names]
if miss: print("WARN not found:", "，".join(miss))
applied=0
for c in cards:
    e=EN.get(c["name"])
    if not e: continue
    if "lesson" in e: c["lesson_en"]=e["lesson"]
    if "summary" in e: c["summary_en"]=e["summary"]
    if "witness" in e: c["witness_en"]=e["witness"]
    if "prayer" in e: c["prayer_en"]=e["prayer"]
    if "follow" in e: c["follow_en"]=e["follow"]
    if "caution" in e: c["caution_en"]=e["caution"]
    if "applications" in e: c["applications_en"]=e["applications"]
    applied+=1
def block(card): return "\n".join(" "+ln for ln in json.dumps(card,ensure_ascii=False,indent=1).splitlines())
src=open(MD,encoding="utf-8").read()
START="export const MIRROR_CHARACTERS = ["; END="\n];\n\nexport const MIRROR_THEMES = ["
open(MD,"w",encoding="utf-8").write(src[:src.index(START)]+START+"\n"+",\n".join(block(c) for c in cards)+src[src.index(END):])
print(f"applied EN fields to {applied}/{len(EN)} cards from {sys.argv[1]}")
