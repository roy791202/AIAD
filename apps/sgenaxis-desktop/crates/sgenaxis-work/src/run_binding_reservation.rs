//! Opaque WORK-owned reservation token for packet-bound run starts.
//!
//! A token is scoped to the `WorkspaceService` instance that created it. Its
//! fields are private so adapters cannot manufacture reservation authority.

use std::sync::Arc;

#[derive(Debug)]
pub struct RunBindingReservation {
    pub(crate) id: u64,
    pub(crate) project_id: String,
    pub(crate) service_identity: Arc<()>,
}

impl RunBindingReservation {
    pub(crate) fn belongs_to(&self, identity: &Arc<()>) -> bool {
        Arc::ptr_eq(&self.service_identity, identity)
    }
}
