#[path = "../src/dispatch.rs"] mod dispatch;
#[path = "../src/dto.rs"] mod dto;
#[path = "../src/git_index_commit.rs"] mod git_index_commit;
use dispatch::DispatchHost;
use sgenaxis_adapters::FakeFileSystem;
use sgenaxis_ports::FileSystemPort;
#[test]
fn presets_and_import_preview_reuse_validated_schema_without_writing() {
 let fs=FakeFileSystem::new();let presets=DispatchHost::project_policy_presets().unwrap();
 assert_eq!(presets["balanced"]["batch"]["maxTasks"],4);
 let bytes=serde_json::to_vec(&presets["balanced"]).unwrap();fs.write_atomic("/selected.json",&bytes).unwrap();let writes=fs.write_count();
 let preview=DispatchHost::project_policy_import(&fs,"/selected.json").unwrap();assert_eq!(preview["status"],"ok");assert_eq!(fs.write_count(),writes);assert_eq!(fs.read("/selected.json").unwrap(),bytes);
}
#[test]
fn imported_secret_field_is_rejected_without_source_mutation() {
 let fs=FakeFileSystem::new();let mut value=DispatchHost::project_policy_presets().unwrap()["balanced"].clone();value["token"]=serde_json::json!("fixture-secret");let bytes=serde_json::to_vec(&value).unwrap();fs.write_atomic("/invalid.json",&bytes).unwrap();let writes=fs.write_count();
 assert!(DispatchHost::project_policy_import(&fs,"/invalid.json").is_err());assert_eq!(fs.write_count(),writes);assert_eq!(fs.read("/invalid.json").unwrap(),bytes);
}
#[test]
fn unbound_or_stale_project_is_rejected_before_any_write() {
 let fs=FakeFileSystem::new();
 assert!(DispatchHost::project_policy_load(&fs,""," ").is_err());
 assert!(DispatchHost::project_policy_save(&fs,"/B","/A",None,b"{}").is_err());assert_eq!(fs.write_count(),0);
}
#[test]
fn current_project_load_save_and_stale_digest() {
 let fs=FakeFileSystem::new();let draft=serde_json::to_vec(&sgenaxis_spec::project_preferences::preset("balanced").unwrap()).unwrap();
 assert_eq!(DispatchHost::project_policy_load(&fs,"/A","/A").unwrap()["configured"],false);
 let saved=DispatchHost::project_policy_save(&fs,"/A","/A",None,&draft).unwrap();
 assert_eq!(saved["preferences"]["batch"]["maxTasks"],4);
 assert_eq!(DispatchHost::project_policy_load(&fs,"/A","/A").unwrap(),saved);
 assert!(DispatchHost::project_policy_save(&fs,"/A","/A",Some("stale"),&draft).is_err());
}
#[test]
fn new_project_choices_are_explicit_and_do_not_touch_host_binding() {
 let fs=FakeFileSystem::new();
 let skip=DispatchHost::project_policy_create(&fs,"/projects","skip",None,None).unwrap();assert_eq!(skip["status"],"ok");
 assert!(!fs.exists("/projects/skip/.sgenaxis/preferences.json").unwrap());
 let preset=DispatchHost::project_policy_create(&fs,"/projects","preset",Some("balanced"),None).unwrap();assert_eq!(preset["status"],"ok");
 assert!(fs.exists("/projects/preset/.sgenaxis/preferences.json").unwrap());
 assert!(DispatchHost::project_policy_create(&fs,"/projects","bad",Some("balanced"),Some("{}")).is_err());
 assert!(!fs.exists("/projects/bad").unwrap());
}
