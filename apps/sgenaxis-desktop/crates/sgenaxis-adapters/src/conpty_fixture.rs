//! Approved EA-A0 ConPTY adapter skeleton. No native operation is implemented.
//! Adapter owns resource tokens; backend is a private acquisition/release test seam.
//! Resource RED proves missing orchestration only, never native ConPTY correctness.
use sgenaxis_ports::{Cleanup, InteractiveError, InteractiveErrorKind, InteractiveFixturePort,
    InteractiveId, InteractiveObservation, InteractiveSize};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ResourceKind { InputRead, InputWrite, OutputRead, OutputWrite, PseudoConsole,
    AttributeList, Process, Thread }
const ACQUISITION_ORDER: [ResourceKind; 8] = [ResourceKind::InputRead,
    ResourceKind::InputWrite, ResourceKind::OutputRead, ResourceKind::OutputWrite,
    ResourceKind::PseudoConsole, ResourceKind::AttributeList, ResourceKind::Process,
    ResourceKind::Thread];

// Private seam; not an additional public architectural Port. A token denotes
// one acquired resource, including the attribute allocation. request_release
// initiates asynchronous teardown once; observe_release only queries progress.
// Observed true releases ownership; false retains it without repeating close.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ResourcePhase { Active, SessionActive(InteractiveId), SessionClosing(InteractiveId),
    SessionFailed(InteractiveId), SessionComplete(InteractiveId), TeardownPending, Failed, Complete }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct OwnedResource { kind: ResourceKind, token: u64, release_requested: bool }

trait ResourceBackend: Send {
    fn acquire(&mut self, kind: ResourceKind) -> Result<u64, InteractiveError>;
    fn request_release(&mut self, kind: ResourceKind, token: u64) -> Result<(), InteractiveError>;
    fn observe_release(&mut self, kind: ResourceKind, token: u64) -> Result<bool, InteractiveError>;

    // Safe private Skeleton seam for the existing InteractiveFixturePort.
    // These defaults intentionally add no behavior or OS calls.
    fn start_session(
        &mut self,
        _: &str,
        _: &str,
        _: InteractiveSize,
    ) -> Result<InteractiveId, InteractiveError> {
        Err(missing(InteractiveErrorKind::Unsupported))
    }
    fn write_session_text(
        &mut self,
        _: InteractiveId,
        _: &str,
    ) -> Result<(), InteractiveError> {
        Err(missing(InteractiveErrorKind::Unsupported))
    }
    fn resize_session(
        &mut self,
        _: InteractiveId,
        _: InteractiveSize,
    ) -> Result<(), InteractiveError> {
        Err(missing(InteractiveErrorKind::Unsupported))
    }
    fn request_session_stop(
        &mut self,
        _: InteractiveId,
    ) -> Result<(), InteractiveError> {
        Err(missing(InteractiveErrorKind::Unsupported))
    }
    fn observe_session(
        &mut self,
        _: InteractiveId,
    ) -> Result<InteractiveObservation, InteractiveError> {
        Err(missing(InteractiveErrorKind::Unsupported))
    }
}
struct UnimplementedBackend;
impl ResourceBackend for UnimplementedBackend {
    fn acquire(&mut self, _: ResourceKind) -> Result<u64, InteractiveError> {
        Err(missing(InteractiveErrorKind::Spawn))
    }
    fn request_release(&mut self, _: ResourceKind, _: u64) -> Result<(), InteractiveError> {
        Err(missing(InteractiveErrorKind::Cleanup))
    }
    fn observe_release(&mut self, _: ResourceKind, _: u64) -> Result<bool, InteractiveError> {
        Err(missing(InteractiveErrorKind::Cleanup))
    }
}
fn missing(kind: InteractiveErrorKind) -> InteractiveError {
    InteractiveError { kind, message: "EA ConPTY resource orchestration not implemented".into() }
}

/// Narrow existing InteractiveFixturePort adapter. Not wired into HOST composition.
/// No native process, pipe, console, worker or fixture is created by this skeleton.
pub struct ConptyFixtureAdapter {
    backend: Box<dyn ResourceBackend>,
    owned: Vec<OwnedResource>,
    phase: ResourcePhase,
    cleanup: Cleanup,
}
impl Default for ConptyFixtureAdapter {
    fn default() -> Self {
        Self { backend: Box::new(UnimplementedBackend), owned: Vec::new(), phase: ResourcePhase::Active, cleanup: Cleanup::Pending }
    }
}
impl ConptyFixtureAdapter {
    // These methods are the actual adapter orchestration seams to fill only
    // after independent RED approval; the tests invoke the existing Port below.
    fn acquire_resources(&mut self, executable: &str, cwd: &str, size: InteractiveSize) -> Result<InteractiveId, InteractiveError> {
        if !self.owned.is_empty() {
            return Err(InteractiveError {
                kind: InteractiveErrorKind::Spawn,
                message: "resource ownership is still unresolved".into(),
            });
        }
        self.phase = ResourcePhase::Active;
        self.cleanup = Cleanup::Pending;
        for kind in ACQUISITION_ORDER {
            match self.backend.acquire(kind) {
                Ok(token) => self.owned.push(OwnedResource {
                    kind, token, release_requested: false,
                }),
                Err(error) => {
                    // The acquisition error remains the start result. Teardown
                    // separately records failure/pending ownership for polling.
                    let _ = self.begin_teardown();
                    return Err(error);
                }
            }
        }
        // Backend success means session setup is ready; retain its resources.
        match self.backend.start_session(executable, cwd, size) {
            Ok(id) => {
                self.phase = ResourcePhase::SessionActive(id);
                Ok(id)
            }
            Err(error) => {
                let _ = self.begin_teardown();
                Err(error)
            }
        }
    }
    fn session_id(&self) -> Option<InteractiveId> {
        match self.phase {
            ResourcePhase::SessionActive(id) | ResourcePhase::SessionClosing(id)
            | ResourcePhase::SessionFailed(id) | ResourcePhase::SessionComplete(id) => Some(id),
            _ => None,
        }
    }
    fn advance_session_teardown(&mut self, id: InteractiveId) -> Result<(), InteractiveError> {
        let result = self.advance_teardown();
        self.phase = match self.cleanup {
            Cleanup::Complete => ResourcePhase::SessionComplete(id),
            Cleanup::Failed => ResourcePhase::SessionFailed(id),
            Cleanup::Pending => ResourcePhase::SessionClosing(id),
        };
        result
    }
    fn begin_teardown(&mut self) -> Result<(), InteractiveError> {
        if matches!(self.phase, ResourcePhase::Complete | ResourcePhase::Failed) {
            return Ok(());
        }
        self.phase = ResourcePhase::TeardownPending;
        self.cleanup = Cleanup::Pending;
        self.advance_teardown()
    }
    fn observe_teardown(&mut self) -> Result<InteractiveObservation, InteractiveError> {
        if self.phase == ResourcePhase::TeardownPending {
            // A backend error is represented by cleanup Failed, not swallowed
            // as success or converted into loss of the outstanding resource.
            let _ = self.advance_teardown();
        }
        Ok(InteractiveObservation {
            output: Vec::new(),
            child_exit: None,
            read_state: sgenaxis_ports::ReadState::Open,
            cleanup: self.cleanup.clone(),
        })
    }
    fn advance_teardown(&mut self) -> Result<(), InteractiveError> {
        while let Some(resource) = self.owned.last_mut() {
            if !resource.release_requested {
                // Mark before the side effect: even an error cannot authorize
                // issuing a second potentially destructive release request.
                resource.release_requested = true;
                if let Err(error) = self.backend.request_release(resource.kind, resource.token) {
                    self.phase = ResourcePhase::Failed;
                    self.cleanup = Cleanup::Failed;
                    return Err(error);
                }
            }
            match self.backend.observe_release(resource.kind, resource.token) {
                Ok(true) => { self.owned.pop(); }
                Ok(false) => {
                    self.cleanup = Cleanup::Pending;
                    return Ok(());
                }
                Err(error) => {
                    self.phase = ResourcePhase::Failed;
                    self.cleanup = Cleanup::Failed;
                    return Err(error);
                }
            }
        }
        self.phase = ResourcePhase::Complete;
        self.cleanup = Cleanup::Complete;
        Ok(())
    }
}
impl InteractiveFixturePort for ConptyFixtureAdapter {
    fn start_fixture(&mut self, executable: &str, cwd: &str, size: InteractiveSize)
        -> Result<InteractiveId, InteractiveError> { self.acquire_resources(executable, cwd, size) }
    fn write_text(&mut self, id: InteractiveId, text: &str) -> Result<(), InteractiveError> {
        if self.phase != ResourcePhase::SessionActive(id) {
            return Err(missing(InteractiveErrorKind::Input));
        }
        self.backend.write_session_text(id, text)
    }
    fn resize(&mut self, id: InteractiveId, size: InteractiveSize) -> Result<(), InteractiveError> {
        if self.phase != ResourcePhase::SessionActive(id) {
            return Err(missing(InteractiveErrorKind::Resize));
        }
        self.backend.resize_session(id, size)
    }
    fn request_stop(&mut self, id: InteractiveId) -> Result<(), InteractiveError> {
        let Some(current) = self.session_id() else { return self.begin_teardown(); };
        if current != id { return Err(missing(InteractiveErrorKind::Stop)); }
        match self.phase {
            ResourcePhase::SessionClosing(_) | ResourcePhase::SessionComplete(_) => return Ok(()),
            ResourcePhase::SessionFailed(_) => return Err(missing(InteractiveErrorKind::Stop)),
            _ => {}
        }
        // Record the request before its side effect so an error cannot repeat it.
        self.phase = ResourcePhase::SessionClosing(id);
        if let Err(error) = self.backend.request_session_stop(id) {
            self.phase = ResourcePhase::SessionFailed(id);
            self.cleanup = Cleanup::Failed;
            return Err(error);
        }
        self.advance_session_teardown(id)
    }
    fn poll(&mut self, id: InteractiveId) -> Result<InteractiveObservation, InteractiveError> {
        let Some(current) = self.session_id() else { return self.observe_teardown(); };
        if current != id { return Err(missing(InteractiveErrorKind::Observe)); }
        let mut observation = match self.backend.observe_session(id) {
            Ok(observation) => observation,
            Err(error) => {
                self.phase = ResourcePhase::SessionFailed(id);
                self.cleanup = Cleanup::Failed;
                return Err(error);
            }
        };
        match self.phase {
            ResourcePhase::SessionComplete(_) => observation.cleanup = Cleanup::Complete,
            ResourcePhase::SessionFailed(_) if observation.cleanup != Cleanup::Complete
                || observation.child_exit.is_none() => {
                observation.cleanup = Cleanup::Failed;
            }
            _ if observation.cleanup == Cleanup::Failed => {
                self.phase = ResourcePhase::SessionFailed(id);
                self.cleanup = Cleanup::Failed;
                observation.cleanup = Cleanup::Failed;
            }
            _ if matches!(self.phase, ResourcePhase::SessionClosing(_))
                || observation.cleanup == Cleanup::Complete => {
                // Backend observations control release readiness. An exit or EOF
                // is never invented from a stop request or an empty output batch.
                let _ = self.advance_session_teardown(id);
                observation.cleanup = self.cleanup.clone();
            }
            _ => {}
        }
        Ok(observation)
    }
}

// Production-bound RED for missing session/IO delegation. This module is
// controlled by in-memory scripts only; it calls the actual adapter through
// InteractiveFixturePort and never invokes Win32 or starts a child.
// Safe Skeleton for the separately approved native anonymous-pipe slice.
// This private seam uses abstract handles only; it performs no Win32 calls.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum PipeApiError { Unsupported, Create, Transfer, Close }
trait PrivatePipeApi: Send {
    type Handle: Copy + Eq + std::fmt::Debug;
    fn create_pipe(&mut self) -> Result<(Self::Handle, Self::Handle), PipeApiError>;
    fn write(&mut self, handle: Self::Handle, bytes: &[u8]) -> Result<usize, PipeApiError>;
    fn read(&mut self, handle: Self::Handle, count: usize) -> Result<Vec<u8>, PipeApiError>;
    fn close(&mut self, handle: Self::Handle) -> Result<(), PipeApiError>;
}
struct OwnedPipeEndpoint<H> { handle: H, close_attempted: bool, unresolved: bool }
struct OwnedPipePair<H> { read: OwnedPipeEndpoint<H>, write: OwnedPipeEndpoint<H> }
// The caller owns this ledger across temporary PipeOwner borrows, including
// after a close failure. It is not a global registry and has no Drop retry.
struct PipeLedger<H> { pairs: Vec<OwnedPipePair<H>>, cleanup: Cleanup }
impl<H> PipeLedger<H> { fn new() -> Self { Self { pairs: Vec::new(), cleanup: Cleanup::Pending } } }
struct PrivatePipeOwner<'a, A: PrivatePipeApi> { api: &'a mut A, ledger: &'a mut PipeLedger<A::Handle> }
impl<'a, A: PrivatePipeApi> PrivatePipeOwner<'a, A> {
    fn new(api: &'a mut A, ledger: &'a mut PipeLedger<A::Handle>) -> Self { Self { api, ledger } }
    fn create_two_pairs(&mut self) -> Result<(), PipeApiError> {
        if self.ledger.pairs.iter().any(|p| [&p.read, &p.write].iter()
            .any(|e| !e.close_attempted || e.unresolved)) {
            return Err(PipeApiError::Create);
        }
        self.ledger.pairs.clear();
        self.ledger.pairs.try_reserve(2).map_err(|_| PipeApiError::Create)?;
        self.ledger.cleanup = Cleanup::Pending;
        for _ in 0..2 {
            // Err carries no endpoints: never inspect failed API out parameters.
            let (read, write) = self.api.create_pipe()?;
            self.ledger.pairs.push(OwnedPipePair {
                read: OwnedPipeEndpoint { handle: read, close_attempted: false, unresolved: false },
                write: OwnedPipeEndpoint { handle: write, close_attempted: false, unresolved: false },
            });
        }
        Ok(())
    }
    fn round_trip(&mut self, index: usize, bytes: &[u8]) -> Result<Vec<u8>, PipeApiError> {
        let pair = self.ledger.pairs.get(index).ok_or(PipeApiError::Transfer)?;
        if pair.read.close_attempted || pair.write.close_attempted {
            return Err(PipeApiError::Transfer);
        }
        if bytes.is_empty() { return Ok(Vec::new()); }
        if bytes.len() > 4096 { return Err(PipeApiError::Transfer); }
        if self.api.write(pair.write.handle, bytes)? != bytes.len() {
            return Err(PipeApiError::Transfer);
        }
        let received = self.api.read(pair.read.handle, bytes.len())?;
        if received.len() != bytes.len() { return Err(PipeApiError::Transfer); }
        Ok(received)
    }
    fn release_all(&mut self) -> Result<(), PipeApiError> {
        let mut failed = false;
        for pair in self.ledger.pairs.iter_mut().rev() {
            for endpoint in [&mut pair.write, &mut pair.read] {
                if endpoint.close_attempted {
                    failed |= endpoint.unresolved;
                    continue;
                }
                // Close failure is indeterminate. Keep the tombstone forever;
                // another pass must never close a potentially recycled handle.
                endpoint.close_attempted = true;
                endpoint.unresolved = true;
                if self.api.close(endpoint.handle).is_ok() {
                    endpoint.unresolved = false;
                } else {
                    failed = true;
                }
            }
        }
        self.ledger.cleanup = if failed { Cleanup::Failed } else { Cleanup::Complete };
        if failed { Err(PipeApiError::Close) } else { Ok(()) }
    }
}

// Private synchronous anonymous-pipe binding; no process or pseudoconsole.
#[cfg(windows)]
#[allow(unsafe_code)]
mod win32_ffi {
    use super::{PrivatePipeApi, PipeApiError};
    use std::{mem::MaybeUninit, ptr};
    use windows_sys::Win32::{Foundation::{CloseHandle, HANDLE},
        Storage::FileSystem::{ReadFile, WriteFile}, System::Pipes::CreatePipe};
    pub(super) struct NativePipeApi;
    impl PrivatePipeApi for NativePipeApi {
        type Handle = usize;
        fn create_pipe(&mut self) -> Result<(usize, usize), PipeApiError> {
            let mut read = MaybeUninit::<HANDLE>::uninit();
            let mut write = MaybeUninit::<HANDLE>::uninit();
            // SAFETY: writable output slots and null optional security attributes.
            // Failed calls leave outputs indeterminate; never inspect them on FALSE.
            if unsafe { CreatePipe(read.as_mut_ptr(), write.as_mut_ptr(), ptr::null(), 4096) } == 0 {
                return Err(PipeApiError::Create);
            }
            // SAFETY: successful CreatePipe initialized both owned handles.
            Ok(unsafe { (read.assume_init() as usize, write.assume_init() as usize) })
        }
        fn write(&mut self, handle: usize, bytes: &[u8]) -> Result<usize, PipeApiError> {
            if bytes.len() > 4096 { return Err(PipeApiError::Transfer); }
            let mut count = 0u32;
            // SAFETY: owner supplies a live synchronous handle; buffer remains valid
            // for the bounded call, count is writable, null OVERLAPPED is synchronous.
            if unsafe { WriteFile(handle as HANDLE, bytes.as_ptr(), bytes.len() as u32,
                &mut count, ptr::null_mut()) } == 0 {
                return Err(PipeApiError::Transfer);
            }
            if count as usize > bytes.len() { return Err(PipeApiError::Transfer); }
            Ok(count as usize)
        }
        fn read(&mut self, handle: usize, count: usize) -> Result<Vec<u8>, PipeApiError> {
            if count > 4096 { return Err(PipeApiError::Transfer); }
            let mut bytes = vec![0u8; count];
            let mut received = 0u32;
            // SAFETY: owner supplies a live synchronous handle and buffer has count
            // initialized writable bytes; output count lives through synchronous call.
            if unsafe { ReadFile(handle as HANDLE, bytes.as_mut_ptr(), count as u32,
                &mut received, ptr::null_mut()) } == 0 {
                return Err(PipeApiError::Transfer);
            }
            if received as usize > count { return Err(PipeApiError::Transfer); }
            bytes.truncate(received as usize);
            Ok(bytes)
        }
        fn close(&mut self, handle: usize) -> Result<(), PipeApiError> {
            // SAFETY: unique owner marks attempted before calling, so even failure
            // cannot cause a retry against a possibly recycled handle value.
            if unsafe { CloseHandle(handle as HANDLE) } == 0 {
                Err(PipeApiError::Close)
            } else { Ok(()) }
        }
    }
    #[cfg(test)]
    mod tests {
        use super::*;
        use super::super::{PrivatePipeOwner, PipeLedger};
        #[test]
        fn native_pipe_fixed_payload_roundtrip() {
            let mut api = NativePipeApi;
            let mut ledger = PipeLedger::new();
            {
                let mut owner = PrivatePipeOwner::new(&mut api, &mut ledger);
                owner.create_two_pairs().expect("two actual anonymous pipe pairs");
                for index in 0..2 {
                    assert_eq!(owner.round_trip(index, b"EA_PIPE_PROOF").unwrap(), b"EA_PIPE_PROOF");
                }
                owner.release_all().expect("all native endpoints closed");
            }
            assert_eq!(ledger.cleanup, super::super::Cleanup::Complete);
            assert!(ledger.pairs.iter().all(|p| [&p.read, &p.write].iter()
                .all(|e| e.close_attempted && !e.unresolved)));
        }
    }
}

// Controlled RED tests call the actual private owner through PrivatePipeApi.
// No Win32, child, or pseudoconsole is invoked.
#[cfg(test)]
mod pipe_owner_red_tests {
    use super::*;
    use std::collections::VecDeque;
    #[derive(Debug, PartialEq, Eq)] enum Call { Create, Write(u64), Read(u64), Close(u64) }
    struct CreateStep { result: Result<(u64, u64), PipeApiError>, bogus: Option<(u64, u64)> }
    #[derive(Default)] struct ControlledPipeApi {
        creates: VecDeque<CreateStep>, calls: Vec<Call>, close_failure: Option<u64>, bytes: Vec<u8>, bogus_outputs: Vec<(u64,u64)>,
    }
    impl PrivatePipeApi for ControlledPipeApi {
        type Handle = u64;
        fn create_pipe(&mut self) -> Result<(u64,u64),PipeApiError> {
            self.calls.push(Call::Create);
            let step=self.creates.pop_front().ok_or(PipeApiError::Create)?;
            if let Some(bogus)=step.bogus { self.bogus_outputs.push(bogus); }
            step.result
        }
        fn write(&mut self, handle:u64, bytes:&[u8])->Result<usize,PipeApiError> {
            self.calls.push(Call::Write(handle)); self.bytes.extend_from_slice(bytes); Ok(bytes.len())
        }
        fn read(&mut self, handle:u64, count:usize)->Result<Vec<u8>,PipeApiError> {
            self.calls.push(Call::Read(handle)); Ok(self.bytes.iter().copied().take(count).collect())
        }
        fn close(&mut self, handle:u64)->Result<(),PipeApiError> {
            self.calls.push(Call::Close(handle));
            if self.close_failure==Some(handle) { Err(PipeApiError::Close) } else { Ok(()) }
        }
    }
    fn endpoint<H>(handle:H)->OwnedPipeEndpoint<H> {
        OwnedPipeEndpoint { handle, close_attempted:false, unresolved:false }
    }

    #[test]
    fn pipe_tpipe01_two_pairs_transfer_bytes_and_release_four_endpoints() {
        let mut api=ControlledPipeApi { creates:VecDeque::from([
            CreateStep { result:Ok((11,12)), bogus:None }, CreateStep { result:Ok((21,22)), bogus:None },
        ]), ..Default::default() };
        let mut ledger=PipeLedger::new();
        {
            let mut owner=PrivatePipeOwner::new(&mut api,&mut ledger);
            owner.create_two_pairs().unwrap();
            assert_eq!(owner.round_trip(0,b"pipe-proof").unwrap(),b"pipe-proof");
            owner.release_all().unwrap();
        }
        assert_eq!(api.calls.iter().filter(|c|matches!(c,Call::Close(_))).count(),4);
        for h in [11,12,21,22] { assert_eq!(api.calls.iter().filter(|c|**c==Call::Close(h)).count(),1); }
        assert_eq!(ledger.cleanup,Cleanup::Complete);
    }

    #[test]
    fn pipe_tpipe02_pair_two_failure_never_uses_false_output_sentinels() {
        let mut api=ControlledPipeApi { creates:VecDeque::from([
            CreateStep { result:Ok((31,32)), bogus:None },
            CreateStep { result:Err(PipeApiError::Create), bogus:Some((0xdead,0xbeef)) },
        ]), ..Default::default() };
        let mut ledger=PipeLedger::new();
        let correct_error; let pair_one_retained_before_release; let valid_pair_closed; let sentinels_unused; let complete;
        {
            let mut owner=PrivatePipeOwner::new(&mut api,&mut ledger);
            let result=owner.create_two_pairs();
            assert_eq!(result,Err(PipeApiError::Create),"owner must observe pair-2 CreatePipe failure");
            correct_error=result==Err(PipeApiError::Create);
            pair_one_retained_before_release=owner.ledger.pairs.len()==1;
            let _=owner.release_all();
            valid_pair_closed=[31,32].iter().all(|h|owner.api.calls.iter().filter(|c|**c==Call::Close(*h)).count()==1);
            sentinels_unused=!owner.api.calls.iter().any(|call|matches!(call,
                Call::Write(0xdead)|Call::Write(0xbeef)|Call::Read(0xdead)|Call::Read(0xbeef)|Call::Close(0xdead)|Call::Close(0xbeef)));
            complete=owner.ledger.cleanup==Cleanup::Complete;
        }
        assert_eq!(api.bogus_outputs,vec![(0xdead,0xbeef)]);
        assert!(correct_error&&pair_one_retained_before_release&&valid_pair_closed&&sentinels_unused&&complete,
            "pair-2 failure releases only acquired pair 1, ignores FALSE outputs, and completes honestly");
    }

    #[test]
    fn pipe_tpipe03_failed_close_keeps_caller_tombstone_without_retry_or_drop_close() {
        let mut api=ControlledPipeApi { creates:VecDeque::from([CreateStep { result:Ok((41,42)), bogus:None }]), close_failure:Some(41), ..Default::default() };
        // Seed the valid owner prestate using handles returned by the fake API.
        let (read,write)=api.create_pipe().unwrap();
        let mut ledger=PipeLedger::new();
        ledger.pairs.push(OwnedPipePair { read:endpoint(read), write:endpoint(write) });
        let cleanup_failed; let tombstone_retained; let one_close_before_drop;
        {
            let mut owner=PrivatePipeOwner::new(&mut api,&mut ledger);
            let _=owner.release_all(); let _=owner.release_all();
            cleanup_failed=owner.ledger.cleanup==Cleanup::Failed;
            tombstone_retained=owner.ledger.pairs.len()==1&&owner.ledger.pairs[0].read.close_attempted&&owner.ledger.pairs[0].read.unresolved;
            one_close_before_drop=owner.api.calls.iter().filter(|c|**c==Call::Close(41)).count()==1;
        }
        let retained_after_drop=ledger.pairs.len()==1&&ledger.pairs[0].read.unresolved;
        let one_close_after_drop=api.calls.iter().filter(|c|**c==Call::Close(41)).count()==1;
        assert!(cleanup_failed&&tombstone_retained&&one_close_before_drop&&retained_after_drop&&one_close_after_drop,
            "failed close retains caller tombstone and is never retried by cleanup or Drop");
    }
}
#[cfg(test)]
mod native_backend_tests {
    use super::*;
    use std::sync::{Arc, Mutex};

    #[derive(Default)]
    struct OperationTrace {
        acquired: Vec<ResourceKind>,
        releases: Vec<(ResourceKind, u64)>,
        events: Vec<String>,
        start_acquired_counts: Vec<usize>,
        starts: Vec<(String, String, InteractiveSize)>,
        writes: Vec<(InteractiveId, String)>,
        resizes: Vec<(InteractiveId, InteractiveSize)>,
        stops: Vec<InteractiveId>,
        polls: Vec<InteractiveId>,
        observation: Option<InteractiveObservation>,
        start_error: Option<InteractiveErrorKind>,
        write_error: Option<InteractiveErrorKind>,
        resize_error: Option<InteractiveErrorKind>,
        stop_error: bool,
        release_pending: bool,
    }

    struct ScriptedBackend {
        trace: Arc<Mutex<OperationTrace>>,
        next_resource: u64,
        next_session_id: u64,
    }

    impl ResourceBackend for ScriptedBackend {
        fn acquire(&mut self, kind: ResourceKind) -> Result<u64, InteractiveError> {
            self.next_resource += 1;
            let mut trace = self.trace.lock().unwrap();
            trace.acquired.push(kind);
            trace.events.push(format!("acquire:{kind:?}"));
            Ok(self.next_resource)
        }

        fn request_release(&mut self, kind: ResourceKind, token: u64) -> Result<(), InteractiveError> {
            let mut trace = self.trace.lock().unwrap();
            trace.releases.push((kind, token));
            trace.events.push(format!("release:{kind:?}:{token}"));
            Ok(())
        }

        fn observe_release(&mut self, _: ResourceKind, _: u64) -> Result<bool, InteractiveError> {
            Ok(!self.trace.lock().unwrap().release_pending)
        }

        fn start_session(
            &mut self,
            executable: &str,
            cwd: &str,
            size: InteractiveSize,
        ) -> Result<InteractiveId, InteractiveError> {
            let mut trace = self.trace.lock().unwrap();
            let acquired_count = trace.acquired.len();
            trace.start_acquired_counts.push(acquired_count);
            trace.starts.push((executable.to_owned(), cwd.to_owned(), size));
            trace.events.push("start_attempt".into());
            if let Some(kind) = trace.start_error.clone() {
                trace.events.push("start_failed_before_reader_ready".into());
                return Err(missing(kind));
            }
            trace.events.push("reader_ready".into());
            self.next_session_id += 1;
            Ok(InteractiveId(self.next_session_id))
        }

        fn write_session_text(
            &mut self,
            id: InteractiveId,
            text: &str,
        ) -> Result<(), InteractiveError> {
            let mut trace = self.trace.lock().unwrap();
            trace.writes.push((id, text.to_owned()));
            if let Some(kind) = trace.write_error.clone() {
                return Err(missing(kind));
            }
            Ok(())
        }

        fn resize_session(
            &mut self,
            id: InteractiveId,
            size: InteractiveSize,
        ) -> Result<(), InteractiveError> {
            let mut trace = self.trace.lock().unwrap();
            trace.resizes.push((id, size));
            if let Some(kind) = trace.resize_error.clone() {
                return Err(missing(kind));
            }
            Ok(())
        }

        fn request_session_stop(
            &mut self,
            id: InteractiveId,
        ) -> Result<(), InteractiveError> {
            let mut trace = self.trace.lock().unwrap();
            trace.stops.push(id);
            if trace.stop_error {
                return Err(missing(InteractiveErrorKind::Stop));
            }
            Ok(())
        }

        fn observe_session(
            &mut self,
            id: InteractiveId,
        ) -> Result<InteractiveObservation, InteractiveError> {
            let mut trace = self.trace.lock().unwrap();
            trace.polls.push(id);
            Ok(trace.observation.clone().unwrap_or(InteractiveObservation {
                output: Vec::new(),
                child_exit: None,
                read_state: sgenaxis_ports::ReadState::Open,
                cleanup: Cleanup::Pending,
            }))
        }
    }

    fn adapter() -> (ConptyFixtureAdapter, Arc<Mutex<OperationTrace>>) {
        let trace = Arc::new(Mutex::new(OperationTrace::default()));
        let adapter = ConptyFixtureAdapter {
            backend: Box::new(ScriptedBackend {
                trace: trace.clone(),
                next_resource: 0,
                next_session_id: 40,
            }),
            owned: Vec::new(),
            phase: ResourcePhase::Active,
            cleanup: Cleanup::Pending,
        };
        (adapter, trace)
    }

    fn start(adapter: &mut ConptyFixtureAdapter) -> InteractiveId {
        adapter.start_fixture(
            "locked-fixture", "isolated-project", InteractiveSize { cols: 80, rows: 25 },
        ).expect("Given a successfully started scripted adapter session")
    }

    fn expected_observation(
        output: &[u8], child_exit: Option<i32>, read_state: sgenaxis_ports::ReadState,
        cleanup: Cleanup,
    ) -> InteractiveObservation {
        InteractiveObservation { output: output.to_vec(), child_exit, read_state, cleanup }
    }

    #[test]
    fn native_red_01_start_retains_all_resources_and_returns_backend_id() {
        let (mut adapter, trace) = adapter();
        let size = InteractiveSize { cols: 80, rows: 25 };
        let actual = adapter.start_fixture("locked-fixture", "isolated-project", size);
        let mut trace = trace.lock().unwrap();
        assert_eq!(trace.acquired, ACQUISITION_ORDER);
        assert_eq!(trace.start_acquired_counts, vec![8], "all setup resources precede child/readiness stage");
        if actual.is_ok() {
            trace.events.push("id_returned_to_port_caller".into());
        }
        let expected_events = ACQUISITION_ORDER.iter().map(|kind| format!("acquire:{kind:?}"))
            .chain(["start_attempt".into(), "reader_ready".into(), "id_returned_to_port_caller".into()])
            .collect::<Vec<_>>();
        assert_eq!(trace.events, expected_events, "id is observable only after setup and reader readiness");
        assert_eq!(actual, Ok(InteractiveId(41)), "start must return the backend session id");
        assert_eq!(adapter.owned.len(), 8, "successful session retains its acquired resource bundle");
        assert_eq!(trace.starts, vec![("locked-fixture".into(), "isolated-project".into(), size)],
            "start must delegate the locked executable, cwd, and dimensions");
        assert!(trace.releases.is_empty(), "successful session must not release its live resources");
    }

    #[test]
    fn native_red_02_failed_session_start_releases_acquired_bundle_without_publishing_id() {
        let (mut adapter, trace) = adapter();
        trace.lock().unwrap().start_error = Some(InteractiveErrorKind::Spawn);
        let actual = adapter.start_fixture(
            "locked-fixture", "isolated-project", InteractiveSize { cols: 80, rows: 25 },
        );
        let trace = trace.lock().unwrap();
        assert_eq!(trace.acquired, ACQUISITION_ORDER);
        assert_eq!(trace.start_acquired_counts, vec![8]);
        assert!(trace.events.contains(&"start_failed_before_reader_ready".into()));
        assert_eq!(trace.releases, ACQUISITION_ORDER.iter().enumerate().rev()
            .map(|(index, kind)| (*kind, (index + 1) as u64)).collect::<Vec<_>>());
        assert_eq!(actual.map_err(|error| error.kind), Err(InteractiveErrorKind::Spawn));
        assert_eq!(adapter.owned.len(), 0, "confirmed cleanup must release all acquired resources");
    }

    #[test]
    fn native_red_03_started_session_forwards_utf8_and_configured_output() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        let text = "你好 fixture\n";
        assert_eq!(adapter.write_text(id, text), Ok(()));
        trace.lock().unwrap().observation = Some(expected_observation(
            b"configured output", None, sgenaxis_ports::ReadState::Open, Cleanup::Pending,
        ));
        assert_eq!(adapter.poll(id), Ok(expected_observation(
            b"configured output", None, sgenaxis_ports::ReadState::Open, Cleanup::Pending,
        )));
        let trace = trace.lock().unwrap();
        assert_eq!(trace.writes, vec![(id, text.into())]);
        assert_eq!(trace.polls, vec![id]);
    }

    #[test]
    fn native_red_04_empty_output_is_open_and_eof_does_not_invent_child_exit() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        trace.lock().unwrap().observation = Some(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Open, Cleanup::Pending,
        ));
        assert_eq!(adapter.poll(id), Ok(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Open, Cleanup::Pending,
        )));
        trace.lock().unwrap().observation = Some(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Eof, Cleanup::Pending,
        ));
        assert_eq!(adapter.poll(id), Ok(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Eof, Cleanup::Pending,
        )));
        assert_eq!(trace.lock().unwrap().polls, vec![id, id]);
    }

    #[test]
    fn native_red_05_resize_forwards_dimensions_and_maps_write_resize_errors() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        let size = InteractiveSize { cols: 120, rows: 40 };
        assert_eq!(adapter.resize(id, size), Ok(()));
        trace.lock().unwrap().resize_error = Some(InteractiveErrorKind::Resize);
        assert_eq!(adapter.resize(id, size).map_err(|error| error.kind), Err(InteractiveErrorKind::Resize));
        trace.lock().unwrap().write_error = Some(InteractiveErrorKind::Input);
        assert_eq!(adapter.write_text(id, "x").map_err(|error| error.kind), Err(InteractiveErrorKind::Input));
        let trace = trace.lock().unwrap();
        assert_eq!(trace.resizes, vec![(id, size), (id, size)]);
        assert_eq!(trace.writes, vec![(id, "x".into())]);
    }

    #[test]
    fn native_red_06_unknown_and_stale_ids_do_not_mutate_live_session() {
        let (mut adapter, trace) = adapter();
        let completed = start(&mut adapter);
        trace.lock().unwrap().observation = Some(expected_observation(
            b"", Some(0), sgenaxis_ports::ReadState::Eof, Cleanup::Complete,
        ));
        let completed_observation = expected_observation(
            b"", Some(0), sgenaxis_ports::ReadState::Eof, Cleanup::Complete,
        );
        assert_eq!(adapter.poll(completed), Ok(completed_observation.clone()));
        assert_eq!(adapter.poll(completed), Ok(completed_observation),
            "polling the same completed session remains idempotently Complete");
        let live = start(&mut adapter);
        assert_ne!(completed, live, "reopened session receives a distinct id");
        let unknown = InteractiveId(99);
        assert!(adapter.write_text(unknown, "unexpected").is_err());
        assert!(adapter.resize(unknown, InteractiveSize { cols: 90, rows: 30 }).is_err());
        assert!(adapter.request_stop(unknown).is_err());
        assert!(adapter.poll(unknown).is_err());
        assert!(adapter.write_text(completed, "stale").is_err());
        assert!(adapter.resize(completed, InteractiveSize { cols: 90, rows: 30 }).is_err());
        assert!(adapter.request_stop(completed).is_err());
        assert!(adapter.poll(completed).is_err());
        assert_eq!(adapter.write_text(live, "new session"), Ok(()));
        let trace = trace.lock().unwrap();
        assert_eq!(trace.writes, vec![(live, "new session".into())],
            "unknown/stale id must not mutate the reopened live session");
        assert!(trace.resizes.is_empty());
        assert!(trace.stops.is_empty());
        assert_eq!(trace.polls, vec![completed, completed],
            "only repeated observation of completed session A reaches the backend");
        assert_eq!(trace.starts, vec![
            ("locked-fixture".into(), "isolated-project".into(), InteractiveSize { cols:80, rows:25 }),
            ("locked-fixture".into(), "isolated-project".into(), InteractiveSize { cols:80, rows:25 }),
        ]);
    }

    #[test]
    fn native_red_07_stop_request_is_distinct_from_child_exit_and_cleanup() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        trace.lock().unwrap().release_pending = true;
        adapter.request_stop(id).expect("stop request should be accepted");
        trace.lock().unwrap().observation = Some(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Open, Cleanup::Pending,
        ));
        assert_eq!(adapter.poll(id), Ok(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Open, Cleanup::Pending,
        )));
        assert_eq!(adapter.owned.len(), 8, "pending cleanup retains session resources");
        assert_eq!(trace.lock().unwrap().stops, vec![id]);
    }

    #[test]
    fn native_red_08_reader_error_does_not_claim_child_exit() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        trace.lock().unwrap().observation = Some(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Error("controlled read error".into()), Cleanup::Pending,
        ));
        assert_eq!(adapter.poll(id), Ok(expected_observation(
            b"", None, sgenaxis_ports::ReadState::Error("controlled read error".into()), Cleanup::Pending,
        )));
        assert_eq!(trace.lock().unwrap().polls, vec![id]);
    }

    #[test]
    fn native_red_09_stop_failure_retains_resources_and_does_not_claim_exit() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        trace.lock().unwrap().stop_error = true;
        let actual = adapter.request_stop(id);
        assert_eq!(
            actual.map_err(|error| error.kind),
            Err(InteractiveErrorKind::Stop),
            "stop must surface the backend's typed failure"
        );
        let trace = trace.lock().unwrap();
        assert_eq!(trace.stops, vec![id]);
        assert!(adapter.owned.len() == 8, "stop failure retains resource ownership");
        assert!(trace.releases.is_empty(), "stop failure must not report destructive release as complete");
    }

    #[test]
    fn native_red_10_poll_preserves_independently_observed_exit() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        let expected = expected_observation(b"configured output", Some(7),
            sgenaxis_ports::ReadState::Eof, Cleanup::Pending);
        trace.lock().unwrap().observation = Some(expected.clone());
        assert_eq!(adapter.poll(id), Ok(expected));
        assert_eq!(trace.lock().unwrap().polls, vec![id]);
    }

    #[test]
    fn native_red_11_stop_and_poll_do_not_repeat_destructive_release() {
        let (mut adapter, trace) = adapter();
        let id = start(&mut adapter);
        trace.lock().unwrap().release_pending = true;
        adapter.request_stop(id).expect("first stop request");
        adapter.request_stop(id).expect("repeated stop request");
        let _ = adapter.poll(id).expect("first observation");
        let _ = adapter.poll(id).expect("repeated observation");
        {
            let trace = trace.lock().unwrap();
            assert_eq!(trace.releases, vec![(ResourceKind::Thread, 8)],
                "pending cleanup requests release once and keeps ownership");
            assert_eq!(adapter.owned.len(), 8);
        }
        {
            let mut trace = trace.lock().unwrap();
            trace.release_pending = false;
            trace.observation = Some(expected_observation(
                b"", Some(0), sgenaxis_ports::ReadState::Eof, Cleanup::Complete,
            ));
        }
        assert_eq!(adapter.poll(id).unwrap().cleanup, Cleanup::Complete);
        assert_eq!(adapter.poll(id).unwrap().cleanup, Cleanup::Complete);
        let trace = trace.lock().unwrap();
        assert_eq!(trace.stops, vec![id], "native stop is issued once per session");
        assert_eq!(trace.releases.iter().map(|(kind, _)| *kind).collect::<Vec<_>>(),
            ACQUISITION_ORDER.iter().rev().copied().collect::<Vec<_>>());
        assert!(adapter.owned.is_empty(), "resources release only after completion is observed");
    }

    #[test]
    fn native_red_12_failed_start_with_pending_release_keeps_owned_prefix() {
        let (mut adapter, trace) = adapter();
        {
            let mut trace = trace.lock().unwrap();
            trace.start_error = Some(InteractiveErrorKind::Spawn);
            trace.release_pending = true;
        }
        let actual = adapter.start_fixture(
            "locked-fixture", "isolated-project", InteractiveSize { cols: 80, rows: 25 },
        );
        assert_eq!(adapter.owned.len(), 8, "unobserved release retains the acquired ownership bundle");
        assert_eq!(adapter.cleanup, Cleanup::Pending);
        {
            let trace = trace.lock().unwrap();
            assert_eq!(trace.releases, vec![(ResourceKind::Thread, 8)],
                "pending start-failure cleanup requests release at most once");
            assert_eq!(trace.start_acquired_counts, vec![8],
                "injected spawn/readiness failure must occur after acquisition and before id publication");
        }
        assert_eq!(actual.map_err(|error| error.kind), Err(InteractiveErrorKind::Spawn));
    }
}

// Recovery contract for a failed stop: retain the session and handle until
// independent observation confirms termination/cleanup; then release safely.
#[cfg(test)]
mod session_cleanup_recovery_tests {
    use super::*;
    use std::sync::{Arc, Mutex};

    #[derive(Default)]
    struct Trace {
        acquired: Vec<ResourceKind>,
        releases: Vec<(ResourceKind, u64)>,
        stop_ids: Vec<InteractiveId>,
        observation: Option<InteractiveObservation>,
        pending: bool,
        release_observe_error: bool,
    }

    struct Backend {
        trace: Arc<Mutex<Trace>>,
        next_resource: u64,
    }

    impl ResourceBackend for Backend {
        fn acquire(&mut self, kind: ResourceKind) -> Result<u64, InteractiveError> {
            self.next_resource += 1;
            self.trace.lock().unwrap().acquired.push(kind);
            Ok(self.next_resource)
        }

        fn request_release(&mut self, kind: ResourceKind, token: u64) -> Result<(), InteractiveError> {
            self.trace.lock().unwrap().releases.push((kind, token));
            Ok(())
        }

        fn observe_release(&mut self, _: ResourceKind, _: u64) -> Result<bool, InteractiveError> {
            let trace = self.trace.lock().unwrap();
            if trace.release_observe_error { Err(missing(InteractiveErrorKind::Cleanup)) }
            else { Ok(!trace.pending) }
        }

        fn start_session(&mut self, _: &str, _: &str, _: InteractiveSize)
            -> Result<InteractiveId, InteractiveError> { Ok(InteractiveId(71)) }

        fn request_session_stop(&mut self, id: InteractiveId) -> Result<(), InteractiveError> {
            self.trace.lock().unwrap().stop_ids.push(id);
            Err(missing(InteractiveErrorKind::Stop))
        }

        fn observe_session(&mut self, _: InteractiveId)
            -> Result<InteractiveObservation, InteractiveError> {
            Ok(self.trace.lock().unwrap().observation.clone().unwrap_or(InteractiveObservation {
                output: Vec::new(), child_exit: None,
                read_state: sgenaxis_ports::ReadState::Open, cleanup: Cleanup::Pending,
            }))
        }
    }

    fn running(trace: Trace) -> (ConptyFixtureAdapter, Arc<Mutex<Trace>>, InteractiveId) {
        let trace = Arc::new(Mutex::new(trace));
        let mut adapter = ConptyFixtureAdapter {
            backend: Box::new(Backend { trace: trace.clone(), next_resource: 0 }),
            owned: Vec::new(), phase: ResourcePhase::Active, cleanup: Cleanup::Pending,
        };
        let id = adapter.start_fixture("locked-fixture", "isolated-project",
            InteractiveSize { cols: 80, rows: 25 }).unwrap();
        (adapter, trace, id)
    }

    fn completed_observation() -> InteractiveObservation {
        // EOF is intentionally not required to confirm child termination/cleanup.
        InteractiveObservation { output: Vec::new(), child_exit: Some(7),
            read_state: sgenaxis_ports::ReadState::Open, cleanup: Cleanup::Complete }
    }

    fn expected_release_order() -> Vec<(ResourceKind, u64)> {
        ACQUISITION_ORDER.iter().enumerate().rev()
            .map(|(index, kind)| (*kind, (index + 1) as u64)).collect()
    }

    #[test]
    fn later_observed_completion_recovers_failed_stop_and_releases_once() {
        let (mut adapter, trace, id) = running(Trace::default());
        assert_eq!(adapter.request_stop(id).map_err(|error| error.kind),
            Err(InteractiveErrorKind::Stop));
        assert_eq!(adapter.owned.len(), 8);
        assert!(trace.lock().unwrap().releases.is_empty());
        assert!(adapter.start_fixture("locked-fixture", "isolated-project",
            InteractiveSize { cols: 80, rows: 25 }).is_err(),
            "unresolved failed session must block reopen");

        trace.lock().unwrap().observation = Some(completed_observation());
        let observed = adapter.poll(id).unwrap();
        assert_eq!(observed.child_exit, Some(7));
        assert_eq!(observed.read_state, sgenaxis_ports::ReadState::Open);
        assert_eq!(observed.cleanup, Cleanup::Complete);
        assert!(adapter.owned.is_empty());
        assert_eq!(trace.lock().unwrap().releases, expected_release_order());
        assert_eq!(trace.lock().unwrap().stop_ids, vec![id], "recovery observes; it does not retry stop");
    }

    #[test]
    fn recovered_stop_with_pending_release_retains_ownership_until_late_confirmation() {
        let (mut adapter, trace, id) = running(Trace { pending: true, ..Trace::default() });
        assert_eq!(adapter.request_stop(id).map_err(|error| error.kind),
            Err(InteractiveErrorKind::Stop));
        trace.lock().unwrap().observation = Some(completed_observation());
        let pending = adapter.poll(id).unwrap();
        assert_eq!(pending.child_exit, Some(7));
        assert_eq!(pending.cleanup, Cleanup::Pending);
        assert_eq!(adapter.owned.len(), 8);
        assert_eq!(trace.lock().unwrap().releases, vec![(ResourceKind::Thread, 8)]);

        trace.lock().unwrap().pending = false;
        let complete = adapter.poll(id).unwrap();
        assert_eq!(complete.child_exit, Some(7));
        assert_eq!(complete.cleanup, Cleanup::Complete);
        assert!(adapter.owned.is_empty());
        assert_eq!(trace.lock().unwrap().releases, expected_release_order());
        assert_eq!(trace.lock().unwrap().stop_ids, vec![id]);
    }

    #[test]
    fn confirmed_exit_with_release_error_keeps_exact_owned_bundle_failed() {
        let (mut adapter, trace, id) = running(Trace { release_observe_error: true, ..Trace::default() });
        assert_eq!(adapter.request_stop(id).map_err(|error| error.kind),
            Err(InteractiveErrorKind::Stop));
        trace.lock().unwrap().observation = Some(completed_observation());
        let failed = adapter.poll(id).unwrap();
        assert_eq!(failed.child_exit, Some(7));
        assert_eq!(failed.cleanup, Cleanup::Failed);
        assert_eq!(adapter.owned.len(), 8);
        assert_eq!(trace.lock().unwrap().releases, vec![(ResourceKind::Thread, 8)]);
        let again = adapter.poll(id).unwrap();
        assert_eq!(again.cleanup, Cleanup::Failed);
        assert_eq!(adapter.owned.len(), 8);
        assert_eq!(trace.lock().unwrap().releases, vec![(ResourceKind::Thread, 8)],
            "failed release is never retried destructively");
    }
    #[test]
    fn cleanup_complete_without_exit_retains_failed_session_until_termination_is_observed() {
        let (mut adapter, trace, id) = running(Trace::default());
        assert_eq!(adapter.request_stop(id).map_err(|error| error.kind),
            Err(InteractiveErrorKind::Stop));
        let complete_without_exit = InteractiveObservation { output: Vec::new(), child_exit: None,
            read_state: sgenaxis_ports::ReadState::Open, cleanup: Cleanup::Complete };
        trace.lock().unwrap().observation = Some(complete_without_exit);
        let pending_stop = adapter.poll(id).unwrap();
        assert_eq!(pending_stop.child_exit, None);
        assert!(matches!(pending_stop.cleanup, Cleanup::Failed | Cleanup::Pending));
        assert_eq!(adapter.owned.len(), 8, "unobserved child termination retains the process/session resources");
        assert!(trace.lock().unwrap().releases.is_empty(), "cleanup alone cannot release a failed-stop child before exit is observed");
        let acquired = trace.lock().unwrap().acquired.len();
        assert!(adapter.start_fixture("locked-fixture", "isolated-project",
            InteractiveSize { cols: 80, rows: 25 }).is_err(), "unresolved session blocks reopen");
        assert_eq!(trace.lock().unwrap().acquired.len(), acquired);

        trace.lock().unwrap().observation = Some(completed_observation());
        let stopped = adapter.poll(id).unwrap();
        assert_eq!(stopped.child_exit, Some(7));
        assert_eq!(stopped.read_state, sgenaxis_ports::ReadState::Open, "EOF is not a cleanup gate");
        assert_eq!(stopped.cleanup, Cleanup::Complete);
        assert!(adapter.owned.is_empty());
        assert_eq!(trace.lock().unwrap().releases, expected_release_order());
    }}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};
    #[derive(Default)]
    pub(super) struct Calls { pub(super) acquired: Vec<ResourceKind>, pub(super) released: Vec<(ResourceKind, u64)>, pub(super) observed: Vec<(ResourceKind, u64)> }
    pub(super) struct ControlledBackend {
        pub(super) calls: Arc<Mutex<Calls>>, pub(super) fail_at: Option<ResourceKind>, pub(super) pending: bool, pub(super) release_error: bool,
    }
    impl ResourceBackend for ControlledBackend {
        fn acquire(&mut self, kind: ResourceKind) -> Result<u64, InteractiveError> {
            let mut c = self.calls.lock().unwrap();
            c.acquired.push(kind);
            if self.fail_at == Some(kind) {
                return Err(InteractiveError { kind: InteractiveErrorKind::Spawn,
                    message: "controlled resource acquisition failure".into() });
            }
            Ok(c.acquired.len() as u64)
        }
        fn request_release(&mut self, kind: ResourceKind, token: u64) -> Result<(), InteractiveError> {
            self.calls.lock().unwrap().released.push((kind, token));
            if self.release_error { return Err(missing(InteractiveErrorKind::Cleanup)); }
            Ok(())
        }
        fn observe_release(&mut self, kind: ResourceKind, token: u64) -> Result<bool, InteractiveError> {
            self.calls.lock().unwrap().observed.push((kind, token));
            if self.release_error { return Err(missing(InteractiveErrorKind::Cleanup)); }
            Ok(!self.pending)
        }
    }
    pub(super) fn adapter(fail_at: Option<ResourceKind>, pending: bool)
        -> (ConptyFixtureAdapter, Arc<Mutex<Calls>>) {
        let calls = Arc::new(Mutex::new(Calls::default()));
        let a = ConptyFixtureAdapter { backend: Box::new(ControlledBackend {
            calls: calls.clone(), fail_at, pending, release_error: false }), owned: Vec::new(), phase: ResourcePhase::Active, cleanup: Cleanup::Pending };
        (a, calls)
    }
    fn failure_at(index: usize) {
        let (mut a, calls) = adapter(Some(ACQUISITION_ORDER[index]), false);
        let e = a.start_fixture("locked-fixture", "isolated-project",
            InteractiveSize { cols: 80, rows: 25 }).unwrap_err();
        assert_eq!(e.kind, InteractiveErrorKind::Spawn);
        let c = calls.lock().unwrap();
        assert_eq!(c.acquired, ACQUISITION_ORDER[..=index],
            "adapter must attempt acquisition through the injected failure stage");
        let expected: Vec<_> = ACQUISITION_ORDER[..index].iter().enumerate()
            .rev().map(|(i, k)| (*k, (i + 1) as u64)).collect();
        assert_eq!(c.released, expected, "only acquired prefix must release exactly once in reverse order");
        assert!(a.owned.is_empty(), "confirmed released prefix must not remain owned");
    }
    macro_rules! failure_case { ($name:ident, $index:expr) => {
        #[test] fn $name() { failure_at($index); }
    }; }
    failure_case!(resource_red_01_input_read_failure, 0);
    failure_case!(resource_red_02_input_write_failure, 1);
    failure_case!(resource_red_03_output_read_failure, 2);
    failure_case!(resource_red_04_output_write_failure, 3);
    failure_case!(resource_red_05_pseudoconsole_failure, 4);
    failure_case!(resource_red_06_attribute_failure, 5);
    failure_case!(resource_red_07_process_failure, 6);
    failure_case!(resource_red_08_thread_failure, 7);

    #[test]
    fn resource_red_09_complete_teardown_is_idempotent() {
        let (mut a, calls) = adapter(None, false);
        a.owned = ACQUISITION_ORDER.iter().enumerate().map(|(i,k)| OwnedResource { kind: *k, token: (i+1) as u64, release_requested: false }).collect();
        assert!(a.request_stop(InteractiveId(1)).is_ok(), "adapter teardown must accept owned resources");
        assert!(a.request_stop(InteractiveId(1)).is_ok(), "repeat stop is idempotent");
        let observation = a.poll(InteractiveId(1)).expect("observe actual adapter teardown");
        assert_eq!(observation.cleanup, Cleanup::Complete);
        assert!(a.owned.is_empty());
        let expected: Vec<_> = ACQUISITION_ORDER.iter().enumerate().rev()
            .map(|(i,k)| (*k,(i+1) as u64)).collect();
        assert_eq!(calls.lock().unwrap().released, expected, "no double release");
    }
    #[test]
    fn resource_red_10_pending_teardown_preserves_ownership() {
        let (mut a, _) = adapter(None, true);
        a.owned = vec![OwnedResource { kind: ResourceKind::PseudoConsole, token: 51, release_requested: false }];
        assert!(a.request_stop(InteractiveId(1)).is_ok(), "begin nonblocking pending teardown");
        let observation = a.poll(InteractiveId(1)).expect("observe pending teardown");
        assert_eq!(observation.cleanup, Cleanup::Pending);
        assert_eq!(a.owned, vec![OwnedResource { kind: ResourceKind::PseudoConsole, token: 51, release_requested: true }], "pending teardown cannot lose resource ownership");
        assert_ne!(a.cleanup, Cleanup::Complete);
    }
}

#[cfg(test)]
mod async_teardown_tests {
    use super::*;
    use super::tests::{adapter, Calls, ControlledBackend};
    use std::sync::{Arc, Mutex};
    fn token(requested: bool) -> OwnedResource {
        OwnedResource { kind: ResourceKind::PseudoConsole, token: 51, release_requested: requested }
    }
    #[test]
    fn resource_red_11_active_poll_never_starts_teardown() {
        let (mut a, calls) = adapter(None, false);
        a.owned = vec![token(false)];
        let observation = a.poll(InteractiveId(1)).expect("Active observation must be non-destructive");
        assert_eq!(observation.cleanup, Cleanup::Pending);
        assert_eq!(a.phase, ResourcePhase::Active);
        assert_eq!(a.owned, vec![token(false)]);
        assert!(calls.lock().unwrap().released.is_empty());
        assert!(calls.lock().unwrap().observed.is_empty());
    }
    #[test]
    fn resource_red_12_pending_repeat_stop_and_poll_never_re_request_release() {
        let (mut a, calls) = adapter(None, true);
        a.owned = vec![token(false)];
        a.request_stop(InteractiveId(1)).expect("initial teardown request");
        assert_eq!(a.phase, ResourcePhase::TeardownPending);
        assert_eq!(a.owned, vec![token(true)]);
        a.request_stop(InteractiveId(1)).expect("idempotent pending stop");
        for _ in 0..2 {
            assert_eq!(a.poll(InteractiveId(1)).unwrap().cleanup, Cleanup::Pending);
        }
        assert_eq!(calls.lock().unwrap().released, vec![(ResourceKind::PseudoConsole, 51)]);
        assert_eq!(a.owned, vec![token(true)]);
    }
    #[test]
    fn resource_red_13_release_failure_retains_ownership_and_never_complete() {
        let calls = Arc::new(Mutex::new(Calls::default()));
        let mut a = ConptyFixtureAdapter { backend: Box::new(ControlledBackend {
            calls, fail_at: None, pending: false, release_error: true }),
            owned: vec![token(false)], phase: ResourcePhase::Active, cleanup: Cleanup::Pending };
        // Port stop only requests cleanup; observation must expose the failure.
        let _ = a.request_stop(InteractiveId(1));
        let observation = a.poll(InteractiveId(1)).expect("release failure is observed cleanup failure");
        assert_eq!(observation.cleanup, Cleanup::Failed);
        assert_eq!(a.phase, ResourcePhase::Failed);
        assert_eq!(a.owned.len(), 1);
        assert_eq!(a.owned[0].token, 51);
        assert_ne!(a.cleanup, Cleanup::Complete);
    }
}

// Independent contract edges. Original thirteen cases above remain exact.
#[cfg(test)]
mod independent_resource_tests {
    use super::*;
    use std::sync::{Arc, Mutex};
    #[derive(Default)]
    struct Trace { acquired: Vec<ResourceKind>, requested: Vec<(ResourceKind,u64)>,
        pending: bool, observe_error: bool, request_error: bool, fail_at: Option<ResourceKind> }
    struct Backend(Arc<Mutex<Trace>>);
    impl ResourceBackend for Backend {
        fn acquire(&mut self, kind: ResourceKind) -> Result<u64,InteractiveError> {
            let mut t=self.0.lock().unwrap(); t.acquired.push(kind);
            if t.fail_at==Some(kind) { return Err(missing(InteractiveErrorKind::Spawn)); }
            Ok(t.acquired.len() as u64)
        }
        fn request_release(&mut self, kind:ResourceKind, token:u64)->Result<(),InteractiveError> {
            let mut t=self.0.lock().unwrap();t.requested.push((kind,token));
            if t.request_error { Err(missing(InteractiveErrorKind::Cleanup)) } else { Ok(()) }
        }
        fn observe_release(&mut self,_:ResourceKind,_:u64)->Result<bool,InteractiveError> {
            let t=self.0.lock().unwrap();
            if t.observe_error { Err(missing(InteractiveErrorKind::Cleanup)) } else { Ok(!t.pending) }
        }
    }
    fn fixture(trace:Trace)->(ConptyFixtureAdapter,Arc<Mutex<Trace>>) {
        let t=Arc::new(Mutex::new(trace));
        (ConptyFixtureAdapter { backend:Box::new(Backend(t.clone())),owned:vec![],
            phase:ResourcePhase::Active,cleanup:Cleanup::Pending },t)
    }
    fn start(a:&mut ConptyFixtureAdapter)->InteractiveError {
        a.start_fixture("locked-fixture","isolated-project",InteractiveSize{cols:80,rows:25})
            .expect_err("resource slice must not fabricate native session success")
    }
    #[test]
    fn resource_edge_14_full_acquire_fails_closed_and_releases_all_once() {
        let (mut a,t)=fixture(Trace::default());
        assert_eq!(start(&mut a).kind,InteractiveErrorKind::Unsupported);
        assert_eq!(t.lock().unwrap().acquired,ACQUISITION_ORDER);
        let expected:Vec<_>=ACQUISITION_ORDER.iter().enumerate().rev()
            .map(|(i,k)|(*k,(i+1)as u64)).collect();
        assert_eq!(t.lock().unwrap().requested,expected);
        assert!(a.owned.is_empty());
        let o=a.poll(InteractiveId(1)).unwrap();
        assert_eq!(o.cleanup,Cleanup::Complete);
        assert_eq!(o.child_exit,None);
        assert_eq!(o.read_state,sgenaxis_ports::ReadState::Open);
    }
    #[test]
    fn resource_edge_15_pending_then_late_observation_releases_without_duplicate_request() {
        let (mut a,t)=fixture(Trace{pending:true,..Trace::default()});
        assert_eq!(start(&mut a).kind,InteractiveErrorKind::Unsupported);
        assert_eq!(a.owned.len(),8);
        assert_eq!(a.poll(InteractiveId(1)).unwrap().cleanup,Cleanup::Pending);
        assert!(a.request_stop(InteractiveId(1)).is_ok());
        assert_eq!(t.lock().unwrap().requested.len(),1);
        t.lock().unwrap().pending=false;
        assert_eq!(a.poll(InteractiveId(1)).unwrap().cleanup,Cleanup::Complete);
        assert!(a.owned.is_empty());
        assert_eq!(t.lock().unwrap().requested.len(),8);
        a.request_stop(InteractiveId(1)).unwrap();a.poll(InteractiveId(1)).unwrap();
        assert_eq!(t.lock().unwrap().requested.len(),8);
    }
    #[test]
    fn resource_edge_16_observe_error_keeps_owned_and_never_false_exit_or_complete() {
        let (mut a,t)=fixture(Trace{observe_error:true,..Trace::default()});
        assert_eq!(start(&mut a).kind,InteractiveErrorKind::Unsupported);
        let o=a.poll(InteractiveId(1)).unwrap();
        assert_eq!(o.cleanup,Cleanup::Failed);
        assert_eq!(o.child_exit,None);
        assert_eq!(o.read_state,sgenaxis_ports::ReadState::Open);
        assert_eq!(a.owned.len(),8);
        assert_eq!(a.phase,ResourcePhase::Failed);
        a.request_stop(InteractiveId(1)).unwrap();a.poll(InteractiveId(1)).unwrap();
        assert_eq!(t.lock().unwrap().requested.len(),1);
    }
    #[test]
    fn resource_edge_17_partial_acquire_release_error_keeps_exact_prefix_owned() {
        let (mut a,t)=fixture(Trace{fail_at:Some(ResourceKind::PseudoConsole),request_error:true,
            ..Trace::default()});
        assert_eq!(start(&mut a).kind,InteractiveErrorKind::Spawn);
        assert_eq!(a.owned.len(),4);
        assert_eq!(a.owned.iter().map(|r|r.kind).collect::<Vec<_>>(),ACQUISITION_ORDER[..4]);
        assert_eq!(a.poll(InteractiveId(1)).unwrap().cleanup,Cleanup::Failed);
        a.request_stop(InteractiveId(1)).unwrap();
        assert_eq!(t.lock().unwrap().requested,vec![(ResourceKind::OutputWrite,4)]);
    }
}
