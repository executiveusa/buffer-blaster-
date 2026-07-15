// Integration test: async job queue contract
// Run: cargo test --manifest-path rust_core/stavarai_core/Cargo.toml --test job_queue

use stavarai_core::job_queue::{JobQueue, JobStatus};
use serde_json::json;

#[test]
fn enqueue_returns_job_id() {
    let q = JobQueue::new();
    let id = q.enqueue("pipeline_run", json!({"client": "brand-a"}));
    assert!(!id.is_empty());
}

#[test]
fn dequeue_returns_pending_job() {
    let q = JobQueue::new();
    let id = q.enqueue("pipeline_run", json!({"client": "brand-a"}));
    let job = q.dequeue().expect("job should be dequeued");
    assert_eq!(job.id, id);
    assert_eq!(job.job_type, "pipeline_run");
    assert_eq!(job.status, JobStatus::Running);
}

#[test]
fn fifo_order_preserved() {
    let q = JobQueue::new();
    let a = q.enqueue("a", json!({}));
    let b = q.enqueue("b", json!({}));
    let c = q.enqueue("c", json!({}));
    assert_eq!(q.dequeue().unwrap().id, a);
    assert_eq!(q.dequeue().unwrap().id, b);
    assert_eq!(q.dequeue().unwrap().id, c);
}

#[test]
fn dequeue_empty_returns_none() {
    let q = JobQueue::new();
    assert!(q.dequeue().is_none());
}

#[test]
fn status_transitions_to_completed() {
    let q = JobQueue::new();
    let id = q.enqueue("task", json!({}));
    q.dequeue();
    q.complete(&id);
    let status = q.status(&id).expect("status should exist");
    assert!(matches!(status, JobStatus::Completed));
}

#[test]
fn status_transitions_to_failed_with_reason() {
    let q = JobQueue::new();
    let id = q.enqueue("task", json!({}));
    q.dequeue();
    q.fail(&id, "video generation timed out");
    let status = q.status(&id).unwrap();
    match status {
        JobStatus::Failed(reason) => assert_eq!(reason, "video generation timed out"),
        other => panic!("expected Failed, got {other:?}"),
    }
}

#[test]
fn job_ids_are_unique() {
    let q = JobQueue::new();
    let a = q.enqueue("t", json!({}));
    let b = q.enqueue("t", json!({}));
    assert_ne!(a, b);
}

#[test]
fn payload_preserved_through_queue() {
    let q = JobQueue::new();
    let payload = json!({"client": "brand-x", "niche": "food-beverage", "n_posts": 15});
    let id = q.enqueue("pipeline_run", payload.clone());
    let job = q.dequeue().unwrap();
    assert_eq!(job.id, id);
    assert_eq!(job.payload, payload);
}
