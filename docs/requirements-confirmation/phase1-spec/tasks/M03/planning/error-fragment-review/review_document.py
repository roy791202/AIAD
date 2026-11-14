"""Review-local restricted schema interpreter; never product behavior or full Draft validation."""
import json,re,hashlib,subprocess,copy,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REPO=ROOT.parents[3]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def valid(s,v):
    if "oneOf" in s:return sum(valid(x,v) for x in s["oneOf"])==1
    if "const" in s:return type(v) is type(s["const"]) and v==s["const"]
    if "enum" in s:return any(type(v)is type(x) and v==x for x in s["enum"])
    if s.get("type")=="string":return isinstance(v,str) and ("pattern" not in s or re.search(s["pattern"],v) is not None)
    if s.get("type")=="object":
        return isinstance(v,dict) and all(k in v for k in s.get("required",[])) and (s.get("additionalProperties") is not False or all(k in s.get("properties",{}) for k in v)) and all(valid(x,v[k]) for k,x in s.get("properties",{}).items() if k in v)
    raise ValueError("unsupported schema: "+str(s))
def run():
    packages=[ROOT/"integration-contract-domain-error-supplement",ROOT/"integration-contract-resource-action-supplement"]
    frozen={str(f.relative_to(REPO)):digest(f) for p in packages+[ROOT/"integration-contract-revision-v3",ROOT/"M03/planning/h2-exact-design"] for f in p.rglob("*") if f.is_file()}
    manifest_results=[]; rows=[]; extra=[]
    for p in packages:
        manifest_results.extend({"path":str(p/n),"match":digest(p/n)==h}for n,h in read(p/"artifact-hashes.json").items())
        schema=read(p/("domain-error.schema.json" if "domain" in p.name else "error-details.schema.json"))
        for f in read(p/"fixtures.json"):
            observed=valid(schema,f["value"]);rows.append({"package":p.name,"id":f["id"],"expected":f["expected"],"observed":observed,"match":observed==f["expected"]})
        sample=read(p/"fixtures.json")[0]["value"]
        for label,mutate in [("outer_extra",lambda x:x.update(extra=True)),("missing_details",lambda x:x.pop("details")),("details_wrong_type",lambda x:x.update(details=[])),("code_wrong_type",lambda x:x.update(code=1))]:
            value=copy.deepcopy(sample);mutate(value);extra.append({"package":p.name,"id":label,"value":value,"expected":False,"observed":valid(schema,value)})
    b=read(ROOT/"M01/planning/s2-green/source-current.json")
    drift=[p for p,h in b["source_hashes"].items()if digest(REPO/p)!=h]
    branch=subprocess.check_output(["git","branch","--show-current"],cwd=REPO,text=True).strip();head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
    result={"stored_fixture_results":rows,"review_added_negative_results":extra,"manifest_results":manifest_results,"source_count":len(b["source_hashes"]),"source_drift":drift,"branch":branch,"head":head,"baseline_identity_match":branch==b["branch"] and head==b["head"],"full_draft2020_12_validator":"NOT RUN; jsonschema unavailable" if not importlib.util.find_spec("jsonschema") else "AVAILABLE BUT NOT RUN","product_tests_build_RED_GREEN_native":"NOT RUN","frozen_before":frozen,"frozen_changed":[p for p,h in frozen.items()if digest(REPO/p)!=h]}
    assert all(r["match"]for r in rows) and all(not r["observed"]for r in extra) and all(r["match"]for r in manifest_results) and not drift and not result["frozen_changed"] and result["baseline_identity_match"]
    return result
if __name__=="__main__":
    result=run();Path(__file__).with_name("verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps({"stored":len(result["stored_fixture_results"]),"review_negative":len(result["review_added_negative_results"]),"source_count":result["source_count"],"drift":result["source_drift"]}))
