//! Injectable clock so debounce tests stay deterministic (no real sleep).

use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

/// Monotonic time source for the listen bridge.
pub trait Clock: Send {
    fn now(&self) -> Instant;
}

/// Wall-clock `Instant::now()`.
#[derive(Debug, Default, Clone, Copy)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now(&self) -> Instant {
        Instant::now()
    }
}

/// Test clock — advance manually; all `now()` share one origin.
#[derive(Debug, Clone)]
pub struct FakeClock {
    origin: Instant,
    offset: Arc<Mutex<Duration>>,
}

impl FakeClock {
    pub fn new() -> Self {
        Self {
            origin: Instant::now(),
            offset: Arc::new(Mutex::new(Duration::ZERO)),
        }
    }

    pub fn advance(&self, by: Duration) {
        let mut o = self.offset.lock().expect("fake clock lock");
        *o = o.saturating_add(by);
    }

    pub fn elapsed(&self) -> Duration {
        *self.offset.lock().expect("fake clock lock")
    }
}

impl Default for FakeClock {
    fn default() -> Self {
        Self::new()
    }
}

impl Clock for FakeClock {
    fn now(&self) -> Instant {
        self.origin + self.elapsed()
    }
}
