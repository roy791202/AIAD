//! IO-PREREQ single-file commit boundary. Pure data and object-safe traits only.
//! Implementations own OS handles and scratch files; no OS types cross here.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommitStage {
    CreateDirectory,
    Acquire,
    Read,
    PrepareOld,
    PrepareNew,
    WritePreparedJournal,
    BeforePublish,
    Publish,
    VerifyPublished,
    WriteCommittedJournal,
    Restore,
    VerifyRestored,
    Cleanup,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitReceipt {
    pub target_path: String,
    pub previous_digest: Option<String>,
    pub committed_digest: String,
    pub transaction_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CommitError {
    InvalidPath {
        reason: String,
    },
    AlreadyExists {
        path: String,
    },
    Busy {
        path: String,
    },
    Conflict {
        expected: Option<String>,
        observed: Option<String>,
    },
    Storage {
        stage: CommitStage,
        path: String,
        reason: String,
    },
    RecoveryRequired {
        target_path: String,
        journal_path: String,
        old_version_path: Option<String>,
        new_version_path: Option<String>,
        reason: String,
    },
}

pub trait FileCommitPort: Send + Sync {
    fn create_directory_exclusive(
        &self,
        parent: &str,
        single_name: &str,
    ) -> Result<String, CommitError>;
    fn acquire_write(&self, path: &str) -> Result<Box<dyn FileWriteLease>, CommitError>;
}

pub trait FileWriteLease {
    fn read_current(&self) -> Result<Option<Vec<u8>>, CommitError>;
    fn replace_checked(
        &mut self,
        expected_digest: Option<&str>,
        bytes: &[u8],
    ) -> Result<CommitReceipt, CommitError>;
}
