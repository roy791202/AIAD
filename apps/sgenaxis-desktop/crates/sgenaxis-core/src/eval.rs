//! Evaluation / propagate — rebuild derived board projection from properties.

use std::collections::BTreeMap;

use crate::projection::{BoardProjection, TaskRecord, Zone};
use crate::property::{PropertyId, PropertyStore, PropertyValue};

/// Rebuild [`BoardProjection`] from task records (property-backed).
pub fn evaluate_board(tasks: &[TaskRecord]) -> BoardProjection {
    let mut proj = BoardProjection::default();
    let mut by_zone: BTreeMap<&'static str, Vec<(String, String)>> = BTreeMap::new();

    for task in tasks {
        match task.zone {
            Zone::Gray => proj.gray += 1,
            Zone::Blue => proj.blue += 1,
            Zone::Yellow => proj.yellow += 1,
            Zone::Red => proj.red += 1,
            Zone::Green => proj.green += 1,
        }
        proj.titles.push(task.title.clone());
        by_zone
            .entry(task.zone.as_str())
            .or_default()
            .push((task.id.clone(), task.title.clone()));
    }

    for (_zone, rows) in by_zone.iter_mut() {
        rows.sort_by(|a, b| a.0.cmp(&b.0));
    }

    proj.titles_by_zone = by_zone
        .into_iter()
        .map(|(z, rows)| (z, rows.into_iter().map(|(_, t)| t).collect()))
        .collect();

    proj
}

/// Read zone / title properties for a task id; returns `None` if incomplete.
pub fn task_from_store(store: &PropertyStore, task_id: &str) -> Option<TaskRecord> {
    let zone_id = PropertyId::task_zone(task_id);
    let title_id = PropertyId::task_title(task_id);
    let zone = store.get(&zone_id).and_then(|v| Zone::parse(v.as_str()))?;
    let title = match store.get(&title_id)? {
        PropertyValue::String(s) => s.clone(),
    };
    Some(TaskRecord {
        id: task_id.to_string(),
        title,
        zone,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evaluate_counts_zones() {
        let tasks = vec![
            TaskRecord {
                id: "a".into(),
                title: "Alpha".into(),
                zone: Zone::Gray,
            },
            TaskRecord {
                id: "b".into(),
                title: "Beta".into(),
                zone: Zone::Yellow,
            },
        ];
        let p = evaluate_board(&tasks);
        assert_eq!(p.gray, 1);
        assert_eq!(p.yellow, 1);
        assert_eq!(p.total_tasks(), 2);
        assert_eq!(p.titles, vec!["Alpha".to_string(), "Beta".to_string()]);
    }
}
