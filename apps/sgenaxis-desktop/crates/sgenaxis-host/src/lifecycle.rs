//! App lifecycle phases — HOST owns boot/shutdown, not business state.

use crate::error::HostError;

/// Observable host phase (BDD-PD-HOST-01: App 可啟動／關閉).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LifecyclePhase {
    Booting,
    Ready,
    ShuttingDown,
    Stopped,
}

impl LifecyclePhase {
    pub fn as_str(self) -> &'static str {
        match self {
            LifecyclePhase::Booting => "booting",
            LifecyclePhase::Ready => "ready",
            LifecyclePhase::ShuttingDown => "shutting_down",
            LifecyclePhase::Stopped => "stopped",
        }
    }
}

/// Pure state machine for app start／close. No OS／Tauri types.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AppLifecycle {
    phase: LifecyclePhase,
}

impl Default for AppLifecycle {
    fn default() -> Self {
        Self::new()
    }
}

impl AppLifecycle {
    /// New host starts in [`LifecyclePhase::Booting`].
    pub fn new() -> Self {
        Self {
            phase: LifecyclePhase::Booting,
        }
    }

    pub fn phase(&self) -> LifecyclePhase {
        self.phase
    }

    /// Booting → Ready (composition root finished wiring).
    pub fn mark_ready(&mut self) -> Result<(), HostError> {
        match self.phase {
            LifecyclePhase::Booting => {
                self.phase = LifecyclePhase::Ready;
                Ok(())
            }
            other => Err(HostError::Lifecycle(format!(
                "cannot mark_ready from {}",
                other.as_str()
            ))),
        }
    }

    /// Ready → ShuttingDown (user／IPC requested close).
    pub fn request_shutdown(&mut self) -> Result<(), HostError> {
        match self.phase {
            LifecyclePhase::Ready => {
                self.phase = LifecyclePhase::ShuttingDown;
                Ok(())
            }
            LifecyclePhase::ShuttingDown => Ok(()),
            other => Err(HostError::Lifecycle(format!(
                "cannot request_shutdown from {}",
                other.as_str()
            ))),
        }
    }

    /// ShuttingDown → Stopped (resources released).
    pub fn mark_stopped(&mut self) -> Result<(), HostError> {
        match self.phase {
            LifecyclePhase::ShuttingDown => {
                self.phase = LifecyclePhase::Stopped;
                Ok(())
            }
            LifecyclePhase::Stopped => Ok(()),
            other => Err(HostError::Lifecycle(format!(
                "cannot mark_stopped from {}",
                other.as_str()
            ))),
        }
    }

    pub fn is_ready(&self) -> bool {
        self.phase == LifecyclePhase::Ready
    }

    pub fn is_stopped(&self) -> bool {
        self.phase == LifecyclePhase::Stopped
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn starts_booting_then_ready_then_stop() {
        let mut life = AppLifecycle::new();
        assert_eq!(life.phase(), LifecyclePhase::Booting);
        life.mark_ready().expect("ready");
        assert!(life.is_ready());
        life.request_shutdown().expect("shutdown");
        assert_eq!(life.phase(), LifecyclePhase::ShuttingDown);
        life.mark_stopped().expect("stopped");
        assert!(life.is_stopped());
    }

    #[test]
    fn rejects_ready_twice() {
        let mut life = AppLifecycle::new();
        life.mark_ready().unwrap();
        assert!(life.mark_ready().is_err());
    }

    #[test]
    fn rejects_shutdown_while_booting() {
        let mut life = AppLifecycle::new();
        assert!(life.request_shutdown().is_err());
    }
}
