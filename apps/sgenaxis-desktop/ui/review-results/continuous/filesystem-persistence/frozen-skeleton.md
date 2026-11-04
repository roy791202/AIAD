# Frozen private skeleton: FS A owner approved

Public API unchanged. Private signatures:
```rust
enum WriteCheckpoint { TempCreated, BeforeWrite, BeforeSync, BeforeRename, BeforeCleanup }
fn temp_candidate(target: &Path) -> PathBuf;
fn write_atomic_with<C,H>(path:&str, contents:&[u8], candidate:C, checkpoint:H)->Result<(),PortError>
where C:FnMut()->PathBuf, H:FnMut(WriteCheckpoint,&Path)->std::io::Result<()>;
```
Candidate called per creation attempt (eventual max128). TempCreated runs after creation with file handle open. BeforeWrite/BeforeSync before corresponding operation. BeforeRename after handle close; ordered release can block there safely. BeforeCleanup after handle close on failure; cleanup callback error must not replace primary error. Test can open append handle at BeforeSync to add partial bytes then return injected failure. Partial-write failure can be emulated at BeforeWrite via fs::write(tmp, partial) then error, with no public IO framework. All closures are invocation-local; no global test state.

Skeleton still File::create (not exclusive), one candidate attempt, missing cleanup on write/sync failures. Intended RED assertion failures: collision sentinel overwritten; failed precommit temp remains. Timeout/deadlock is not valid RED. Tests are std_fs.rs child using super, path std_fs_tests.rs. Test owner may add cfg(test) registration after file exists. No final production behavior until parent verifies RED.
