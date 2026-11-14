[Phase: Green]
[Status: OK]

OWNER_APPROVED_A; implemented after verified RED; independent focused13/workspace290/EXEC56/Tauri79 and architecture review PASS; yellow owner acceptance pending. Canonical structured model: module.json; generated human surface: module.html.

## A1 System context
Existing HOST document/settings save callers invoke FileSystemPort. Only real StdFileSystem implementation changes; no UI or generic save redesign.

## A2 Hexagonal system boundary
Driving UI/CLI -> existing HOST use cases -> FileSystemPort <- StdFileSystem -> OS filesystem. Domain has no filesystem dependency.

## A3 Module dependency
HOST -> sgenaxis-ports; sgenaxis-adapters -> sgenaxis-ports and std. No application -> concrete adapter dependency added.

## A4 Responsibilities
Caller owns save intent and payload. FileSystemPort owns opaque IO contract. StdFileSystem owns one write transaction and temporary file lifecycle. OS implements rename.

## A5 Input ports
Existing FileSystemPort::write_atomic(path:&str, contents:&[u8])->Result<(),PortError>; no signature changes.

## A6 Output ports
No new output ports; adapter calls std::fs/OpenOptions/Write behind existing IO boundary.

## A7 Driving adapters
Existing UI/CLI/HOST callers unchanged; tests call FileSystemPort.

## A8 Driven adapters
StdFileSystem only. FakeFileSystem unchanged; real adapter tests establish OS-specific guarantees.

## A9 Dependency direction
Caller -> existing port <- real adapter -> standard library/OS. Domain and HOST never acquire concrete filesystem dependency.

## A10 State ownership
Destination is committed persistent state; caller owns submitted byte slice. Each invocation exclusively owns its temp path and open handle; no authoritative global state. Atomic counter, if used, is naming assistance only; create_new decides ownership.

## A11 Mutation boundary
Only owning invocation writes/removes its temporary file. Destination changes only at successful rename. Never delete destination as replacement fallback.

## A12 Transaction boundary
Create sibling exclusively -> write all -> sync file -> close -> rename over destination. Before successful rename, prior destination bytes remain unchanged. Error cleanup removes only owned temp, best effort; cannot promise cleanup if OS denies removal.

## A13 External system boundary
Local filesystem behavior; Windows machine probe only. Network filesystems, adversarial directory mutation, symlink sandboxing, power loss and parent-directory fsync excluded.

## A14 Forbidden dependencies
No new Manager/service/port/crate, per-target lock table, serialization change, CAS/version arbitration, background cleanup daemon, caller rewrite, public error variant, or remove-destination fallback.

Owner approved A. Independent RED verified before production body implementation; independent GREEN/review passed; owner acceptance remains pending.
