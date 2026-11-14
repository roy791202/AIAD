//! Independent acceptance tests for owner-approved read-only A envelope.
use std::sync::{Mutex,atomic::{AtomicUsize,Ordering}};
use sgenaxis_ports::{FileSystemPort,PortError};
use sgenaxis_adapters::ess_codec::ProductEssDecoder;
use sgenaxis_spec::packet::*;
use sgenaxis_host::module_packet::{export_module_packet,check_module_packet_freshness};
const XML: &str = include_str!("fixtures/module_packet.ess");
#[test]
fn extra_structure_validation_and_selectors() {
    let lf = XML.replace("\r\n", "\n");
    let crlf = lf.replace('\n', "\r\n");
    for xml in [&lf, &crlf] {
        for (from, to, expected) in [
            ("<architecture encoding=\"xml\">", "<architecture encoding=\"json\">", "UNSUPPORTED_FORMAT"),
            ("<eluslotScene ", "<eluslotScene xmlns=\"urn:other\" ", "UNSUPPORTED_FORMAT"),
            ("<node id=\"layer\"", "<node id=\"\"", "INVALID_IDENTITY"),
            ("target=\"outside\"", "target=\"absent\"", "MISSING_REFERENCE"),
            ("kind=\"Layer\"", "kind=\"Command\"", "INVALID_DOCUMENT"),
        ] {
            assert!(xml.contains(from), "fixture mutation target absent: {from}");
            let mutated = xml.replace(from, to);
            assert_ne!(&mutated, xml, "fixture mutation did not apply");
            code(export(&mutated), expected);
        }
    }
    fn selectors(n: &SourceElement, out: &mut Vec<String>) {
        out.push(n.selector.clone());
        for child in &n.children { selectors(child, out); }
    }
    let packet = export(XML).unwrap();
    let mut selected = vec![];
    for node in &packet.nodes { selectors(node, &mut selected); }
    assert!(selected.iter().all(|value| value.starts_with("/eluslotScene[1]/architecture[1]/eluslotArch[1]/nodes[1]/node[")));
    let mut unique = selected.clone();
    unique.sort();
    unique.dedup();
    assert_eq!(selected.len(), unique.len());
}
// Independent review regressions; original twelve cases remain unchanged.
#[test] fn literal_dtd_text_inside_cdata_is_not_declaration(){let xml=XML.replace("Given valid scene","<![CDATA[Given literal <!DOCTYPE example>]]>");let p=export(&xml).unwrap();assert!(serde_json::to_string(&p).unwrap().contains("Given literal <!DOCTYPE example>"));}
#[test] fn semantic_module_endpoint_is_boundary_context(){let xml=XML.replace("</nodes><edges>","<node id=\"semantic-A\" kind=\"Module\"><inputs><port id=\"module-in\" direction=\"input\"/></inputs></node></nodes><edges><edge id=\"module-boundary\" fromNode=\"outside\" fromPort=\"outside-out\" toNode=\"semantic-A\" toPort=\"module-in\"/>");let p=export(&xml).unwrap();assert!(p.boundary_edges.iter().any(|e|e.attributes.get("id").map(String::as_str)==Some("module-boundary")));assert!(!p.nodes.iter().any(|n|n.attributes.get("id").map(String::as_str)==Some("semantic-A")));}
struct Fs { bytes: Mutex<Vec<u8>>, next: Mutex<Option<Vec<u8>>>, reads: AtomicUsize, writes: AtomicUsize, fail: bool }
impl Fs { fn new(b: impl AsRef<[u8]>) -> Self { Self { bytes:Mutex::new(b.as_ref().to_vec()),next:Mutex::new(None),reads:AtomicUsize::new(0),writes:AtomicUsize::new(0),fail:false } } }
impl FileSystemPort for Fs {
 fn read(&self,_:&str)->Result<Vec<u8>,PortError>{ let n=self.reads.fetch_add(1,Ordering::SeqCst); if self.fail{return Err(PortError::PermissionDenied("fixture".into()))} if n>0 {if let Some(b)=self.next.lock().unwrap().take(){*self.bytes.lock().unwrap()=b;}} Ok(self.bytes.lock().unwrap().clone()) }
 fn read_to_string(&self,p:&str)->Result<String,PortError>{String::from_utf8(self.read(p)?).map_err(|e|PortError::Io(e.to_string()))}
 fn exists(&self,_:&str)->Result<bool,PortError>{Ok(true)} fn is_file(&self,_:&str)->Result<bool,PortError>{Ok(true)}
 fn write_atomic(&self,_:&str,_:&[u8])->Result<(),PortError>{self.writes.fetch_add(1,Ordering::SeqCst);panic!("read-only violation")}
 fn create_dir_all(&self,_:&str)->Result<(),PortError>{panic!("read-only violation")} fn remove_file(&self,_:&str)->Result<(),PortError>{panic!("read-only violation")}
}
fn req()->ExportRequest{ExportRequest{relative_path:"scene/product.ess".into(),module_id:"semantic-A".into(),task_id:"TASK-A".into(),expected_source_sha256:None,limits:PacketLimits::default()}}
fn export(xml:&str)->Result<ModulePacket,PacketError>{export_module_packet(&Fs::new(xml),&ProductEssDecoder,"D:/project",&req())}
fn code(result:Result<ModulePacket,PacketError>,expected:&str){let e=result.unwrap_err();assert_eq!(e.code,expected,"{e}");assert!(!e.message.is_empty());}
#[test] fn selected_module_preserves_facts_excludes_unrelated_and_never_grants_approval(){
 let fs=Fs::new(XML);let p=export_module_packet(&fs,&ProductEssDecoder,"D:/project",&req()).unwrap();
 assert_eq!(p.module.module_id,"semantic-A");assert_eq!(p.module.slot_id,"slot-Z");assert_eq!(p.module.layer_id,"layer");assert_eq!(p.nodes.len(),2);assert_eq!(p.internal_edges.len(),1);assert_eq!(p.boundary_edges.len(),1);assert_eq!(p.readiness,PacketReadiness::NotReady);
 let json=serde_json::to_string(&p).unwrap(); for value in ["captured","Preserve old state","Given valid scene","failure preserves state","cmd-in","schemaRef","Selected task"]{assert!(json.contains(value),"missing {value}");} for value in ["UNRELATED_NODE_SECRET","UNRELATED_TASK_SECRET","UNRELATED_DESIGN_SECRET"]{assert!(!json.contains(value),"leaked {value}");}
 assert!(p.nodes.iter().all(|n|!n.selector.is_empty()));assert_eq!(p.source.sha256,source_sha256(XML.as_bytes()));assert_eq!(p.ui_context.len(),1);assert_eq!(p.ui_context[0].document_ref,"embedded-design");assert!(p.diagnostics.iter().any(|d|d.code=="UI_SCOPE_UNRESOLVED"));assert!(p.diagnostics.len()>=3);assert_eq!(fs.writes.load(Ordering::SeqCst),0);assert!(fs.reads.load(Ordering::SeqCst)>=2);
}
#[test] fn deterministic_payload_and_known_sha256(){assert_eq!(source_sha256(b"abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");let a=export(XML).unwrap();let b=export(XML).unwrap();assert_eq!(a,b);let mut unsigned=a.clone();unsigned.payload_sha256.clear();assert_eq!(a.payload_sha256,source_sha256(&serde_json::to_vec(&unsigned).unwrap()));}
#[test] fn empty_module_and_missing_task_are_diagnostics(){let mut r=req();r.module_id="empty-module".into();r.task_id="absent".into();let p=export_module_packet(&Fs::new(XML),&ProductEssDecoder,"D:/project",&r).unwrap();assert!(p.nodes.is_empty());assert!(p.task.is_none());assert!(p.diagnostics.len()>=4);assert_eq!(p.readiness,PacketReadiness::NotReady);}
#[test] fn invalid_paths_reject_before_io(){for path in ["","../x.ess","/x.ess","C:/x.ess","scene/C:/x.ess","scene/x:ads.ess","\\\\server\\x.ess"]{let fs=Fs::new(XML);let mut r=req();r.relative_path=path.into();code(export_module_packet(&fs,&ProductEssDecoder,"D:/project",&r),if path.is_empty(){"INVALID_REQUEST"}else{"INVALID_PATH"});assert_eq!(fs.reads.load(Ordering::SeqCst),0,"{path}");}}
#[test] fn empty_identity_and_zero_limits_reject_before_io(){for i in 0..6{let fs=Fs::new(XML);let mut r=req();let root=if i==0{""}else{"D:/project"};match i{1=>r.module_id.clear(),2=>r.task_id.clear(),3=>r.limits.max_source_bytes=0,4=>r.limits.max_depth=0,5=>r.limits.max_elements=0,_=>()};code(export_module_packet(&fs,&ProductEssDecoder,root,&r),"INVALID_REQUEST");assert_eq!(fs.reads.load(Ordering::SeqCst),0);}}
#[test] fn unsupported_extension_and_read_failure(){let fs=Fs::new(XML);let mut r=req();r.relative_path="x.esml".into();code(export_module_packet(&fs,&ProductEssDecoder,"D:/project",&r),"UNSUPPORTED_SOURCE");let mut fs=Fs::new(XML);fs.fail=true;code(export_module_packet(&fs,&ProductEssDecoder,"D:/project",&req()),"SOURCE_READ_FAILED");}
#[test] fn source_staleness_change_and_freshness_binding(){let mut r=req();r.expected_source_sha256=Some("0".repeat(64));code(export_module_packet(&Fs::new(XML),&ProductEssDecoder,"D:/project",&r),"PACKET_STALE");let fs=Fs::new(XML);*fs.next.lock().unwrap()=Some(XML.replace("Selected task","changed").into_bytes());code(export_module_packet(&fs,&ProductEssDecoder,"D:/project",&req()),"SOURCE_CHANGED");let p=export(XML).unwrap();assert_eq!(check_module_packet_freshness(&Fs::new(XML),"D:/project",&p).unwrap(),PacketFreshness::Current);assert_eq!(check_module_packet_freshness(&Fs::new("changed"),"D:/project",&p).unwrap(),PacketFreshness::Stale);assert_eq!(check_module_packet_freshness(&Fs::new(XML),"D:/other",&p).unwrap_err().code,"SOURCE_BINDING_MISMATCH");}
#[test] fn malformed_dtd_utf8_and_versions(){for (bytes,expected) in [(b"<broken".to_vec(),"INVALID_XML"),(vec![255],"INVALID_XML"),(XML.replace("<eluslotScene","<!DOCTYPE eluslotScene [<!ENTITY x 'expansion'>]><eluslotScene").into_bytes(),"XML_DTD_FORBIDDEN"),(XML.replacen("formatVersion=\"1\"","formatVersion=\"99\"",1).into_bytes(),"UNSUPPORTED_FORMAT"),(XML.replacen("eluslot.ess","unknown",1).into_bytes(),"UNSUPPORTED_FORMAT")]{code(export_module_packet(&Fs::new(bytes),&ProductEssDecoder,"D:/project",&req()),expected);}}
#[test] fn duplicate_identity_categories_reject(){for (a,b) in [("id=\"outside\" kind","id=\"command\" kind"),("moduleId=\"empty-module\"","moduleId=\"semantic-A\""),("slotId=\"empty-slot\"","slotId=\"slot-Z\""),("id=\"boundary\"","id=\"internal\""),("id=\"outside-out\"","id=\"cmd-out\"")]{code(export(&XML.replace(a,b)),"DUPLICATE_ID");}}
#[test] fn membership_and_graph_references_reject(){for (a,b,c) in [("<member id=\"ui\"/>","<member id=\"absent\"/>","MISSING_REFERENCE"),("moduleRef=\"semantic-A\" layerRef=\"layer\"","moduleRef=\"empty-module\" layerRef=\"layer\"","MEMBERSHIP_MISMATCH"),("toNode=\"ui\"","toNode=\"absent\"","MISSING_REFERENCE"),("fromPort=\"cmd-out\"","fromPort=\"cmd-in\"","MISSING_REFERENCE")]{code(export(&XML.replace(a,b)),c);}}
#[test] fn parse_limits_boundaries(){let decoder=ProductEssDecoder;let mut l=PacketLimits::default();l.max_source_bytes=XML.len();assert!(decoder.decode(XML.as_bytes(),&l).is_ok());l.max_source_bytes=XML.len()-1;assert_eq!(decoder.decode(XML.as_bytes(),&l).unwrap_err().code,"SOURCE_TOO_LARGE");let tiny=b"<a><b/></a>";l=PacketLimits{max_source_bytes:tiny.len(),max_depth:2,max_elements:2};assert!(decoder.decode(tiny,&l).is_ok());l.max_depth=1;assert_eq!(decoder.decode(tiny,&l).unwrap_err().code,"XML_LIMIT_EXCEEDED");l.max_depth=2;l.max_elements=1;assert_eq!(decoder.decode(tiny,&l).unwrap_err().code,"XML_LIMIT_EXCEEDED");}
#[test] fn ui_absence_diagnostic_without_unrelated_design_dump(){let xml=XML.replace("uiDefinitionRef=\"embedded-design\"","");let p=export(&xml).unwrap();assert!(p.diagnostics.iter().any(|d|d.code=="UI_DOCUMENT_UNRESOLVED"));assert!(!serde_json::to_string(&p).unwrap().contains("UNRELATED_DESIGN_SECRET"));}

