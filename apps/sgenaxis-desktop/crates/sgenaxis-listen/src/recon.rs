//! PD-LISTEN-RECON-01 — run-end reconciliation helpers.
//!
//! When a listened agent process ends abnormally, emit a reconcile domain
//! signal whose classification mirrors EXEC [`ExitClassification`]. Success
//! ends mark the run finished without a reconcile event.

use sgenaxis_exec::ExitClassification;

/// True when the EXEC end class requires listen-side reconciliation.
///
/// Success is a clean finish (no 待對帳). Cancelled／Failure／Crashed all need
/// accounting before any re-dispatch (PRODUCT-DEVELOPMENT: 取消與崩潰要對帳).
pub fn needs_reconcile(classification: ExitClassification) -> bool {
    !matches!(classification, ExitClassification::Success)
}

/// Stable projection label matching EXEC classification names.
pub fn classification_label(classification: ExitClassification) -> &'static str {
    match classification {
        ExitClassification::Success => "success",
        ExitClassification::Failure => "failure",
        ExitClassification::Cancelled => "cancelled",
        ExitClassification::Crashed => "crashed",
    }
}

/// Whether an [`crate::source::SourceEvent::Agent`] chunk is terminal for a run.
pub fn is_terminal_chunk(chunk: &sgenaxis_exec::AgentChunk) -> bool {
    matches!(
        chunk,
        sgenaxis_exec::AgentChunk::Exited { .. } | sgenaxis_exec::AgentChunk::Failed { .. }
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn success_does_not_need_reconcile() {
        assert!(!needs_reconcile(ExitClassification::Success));
    }

    #[test]
    fn abnormal_classes_need_reconcile() {
        assert!(needs_reconcile(ExitClassification::Crashed));
        assert!(needs_reconcile(ExitClassification::Cancelled));
        assert!(needs_reconcile(ExitClassification::Failure));
    }

    #[test]
    fn labels_match_exec_names() {
        assert_eq!(classification_label(ExitClassification::Crashed), "crashed");
        assert_eq!(classification_label(ExitClassification::Cancelled), "cancelled");
    }
}
