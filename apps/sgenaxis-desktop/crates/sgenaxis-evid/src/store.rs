//! Immutable evidence write + index. Append-only; history is never overwritten.

use std::collections::BTreeMap;

use crate::binding::VersionBinding;
use crate::capture::RunCapture;
use crate::classify::{classify_capture, is_valid_behavioral_red, OutcomeClass};

/// Stable evidence id (caller-supplied or generated).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Ord, PartialOrd)]
pub struct EvidenceId(pub String);

/// Stored verdict derived from classification (never conflates the three failure classes).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvidenceVerdict {
    Pass,
    BehavioralRed,
    InfraFailure { reason: String },
    NotMeasured,
}

impl From<OutcomeClass> for EvidenceVerdict {
    fn from(c: OutcomeClass) -> Self {
        match c {
            OutcomeClass::Pass => EvidenceVerdict::Pass,
            OutcomeClass::BehavioralRed => EvidenceVerdict::BehavioralRed,
            OutcomeClass::InfraFailure { reason } => EvidenceVerdict::InfraFailure { reason },
            OutcomeClass::NotMeasured => EvidenceVerdict::NotMeasured,
        }
    }
}

/// One immutable evidence record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceRecord {
    pub id: EvidenceId,
    pub bdd_id: Option<String>,
    pub verdict: EvidenceVerdict,
    pub binding: VersionBinding,
    pub capture: RunCapture,
    /// True only when verdict is BehavioralRed **and** a BDD id was linked.
    pub red_qualified: bool,
}

/// Errors from evidence commands.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvidError {
    /// Infra / empty outcomes cannot be recorded as valid behavioral RED.
    RedNotQualified(String),
    /// Behavioral RED requires a BDD link.
    MissingBddLink,
    DuplicateId(String),
}

impl std::fmt::Display for EvidError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EvidError::RedNotQualified(r) => write!(f, "not RED-qualified: {r}"),
            EvidError::MissingBddLink => write!(f, "behavioral RED requires bdd_id link"),
            EvidError::DuplicateId(id) => write!(f, "duplicate evidence id: {id}"),
        }
    }
}

impl std::error::Error for EvidError {}

/// In-memory evidence store: write then index; never mutates prior records.
#[derive(Debug, Default)]
pub struct EvidenceStore {
    records: Vec<EvidenceRecord>,
    by_id: BTreeMap<String, usize>,
    by_bdd: BTreeMap<String, Vec<usize>>,
}

impl EvidenceStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn len(&self) -> usize {
        self.records.len()
    }

    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    pub fn get(&self, id: &str) -> Option<&EvidenceRecord> {
        self.by_id.get(id).map(|&i| &self.records[i])
    }

    pub fn records_for_bdd(&self, bdd_id: &str) -> Vec<&EvidenceRecord> {
        self.by_bdd
            .get(bdd_id)
            .map(|idxs| idxs.iter().map(|&i| &self.records[i]).collect())
            .unwrap_or_default()
    }

    /// Classify + append a general evidence record (any outcome class).
    pub fn record(
        &mut self,
        id: impl Into<String>,
        bdd_id: Option<String>,
        binding: VersionBinding,
        capture: RunCapture,
    ) -> Result<&EvidenceRecord, EvidError> {
        let id_str = id.into();
        if self.by_id.contains_key(&id_str) {
            return Err(EvidError::DuplicateId(id_str));
        }
        let class = classify_capture(&capture);
        let verdict = EvidenceVerdict::from(class);
        let red_qualified = matches!(verdict, EvidenceVerdict::BehavioralRed) && bdd_id.is_some();

        let record = EvidenceRecord {
            id: EvidenceId(id_str.clone()),
            bdd_id: bdd_id.clone(),
            verdict,
            binding,
            capture,
            red_qualified,
        };
        let idx = self.records.len();
        self.records.push(record);
        self.by_id.insert(id_str, idx);
        if let Some(ref bdd) = bdd_id {
            self.by_bdd.entry(bdd.clone()).or_default().push(idx);
        }
        Ok(&self.records[idx])
    }

    /// Record a **valid behavioral RED** linked to a BDD. Rejects infra / empty / pass.
    pub fn record_behavioral_red(
        &mut self,
        id: impl Into<String>,
        bdd_id: impl Into<String>,
        binding: VersionBinding,
        capture: RunCapture,
    ) -> Result<&EvidenceRecord, EvidError> {
        let bdd = bdd_id.into();
        if bdd.trim().is_empty() {
            return Err(EvidError::MissingBddLink);
        }
        let class = classify_capture(&capture);
        if !is_valid_behavioral_red(&class) {
            let reason = match &class {
                OutcomeClass::InfraFailure { reason } => {
                    format!("infra:{reason}")
                }
                OutcomeClass::NotMeasured => "empty_or_not_measured".into(),
                OutcomeClass::Pass => "was_pass_not_red".into(),
                OutcomeClass::BehavioralRed => unreachable!(),
            };
            return Err(EvidError::RedNotQualified(reason));
        }
        self.record(id, Some(bdd), binding, capture)
    }

    /// Latest record for a BDD that matches `current` binding (if any).
    pub fn latest_matching(
        &self,
        bdd_id: &str,
        current: &VersionBinding,
    ) -> Option<&EvidenceRecord> {
        self.records_for_bdd(bdd_id)
            .into_iter()
            .rev()
            .find(|r| r.binding.matches_current(current))
    }
}
