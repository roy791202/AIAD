//! Dirty tracking — which properties (and derived sinks) need re-evaluation.

use std::collections::HashSet;

use crate::property::PropertyId;

/// Set of dirty property ids plus a flag for the board projection sink.
#[derive(Debug, Default, Clone)]
pub struct DirtySet {
    props: HashSet<PropertyId>,
    projection: bool,
}

impl DirtySet {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn mark_property(&mut self, id: PropertyId) {
        self.props.insert(id);
        // Any property change invalidates the board projection for this card.
        self.projection = true;
    }

    pub fn mark_projection(&mut self) {
        self.projection = true;
    }

    pub fn is_property_dirty(&self, id: &PropertyId) -> bool {
        self.props.contains(id)
    }

    pub fn is_projection_dirty(&self) -> bool {
        self.projection
    }

    pub fn is_empty(&self) -> bool {
        self.props.is_empty() && !self.projection
    }

    pub fn clear(&mut self) {
        self.props.clear();
        self.projection = false;
    }

    pub fn dirty_property_count(&self) -> usize {
        self.props.len()
    }
}
